"""Public STAC Sentinel-2 pixel sampling + public terrain tiles (prototype).

No Earth Engine credentials required. Samples *one* cloud-screened pixel at
a supplied coordinate, not a regional composite or forest map. Backend reads
remote Cloud Optimized GeoTIFF ranges; availability, terms and quota can vary.
"""
from datetime import date, timedelta
from functools import lru_cache
from io import BytesIO
from math import asinh, atan, cos, degrees, floor, log, pi, radians, sin, tan
from urllib.parse import urlparse
import requests
from fastapi import HTTPException
from PIL import Image
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
TERRAIN_BASE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium"
BAND_ASSETS = {
    "B2": "blue", "B3": "green", "B4": "red",
    "B5": "rededge1", "B6": "rededge2", "B7": "rededge3",
    "B8": "nir", "B8A": "nir08", "B11": "swir16", "B12": "swir22"
}
CLEAR_SCL = {4, 5, 6, 7}
MAX_SCENES = 6

class SourceError(Exception):
    pass

def _safe_asset_url(url):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    # Only the public Element84 Sentinel imagery bucket. No arbitrary URLs
    # from upstream STAC responses are passed to GDAL.
    allowed = host in {
        "e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com",
        "sentinel-cogs.s3.us-west-2.amazonaws.com",
        "e84-earth-search-sentinel-data.s3.amazonaws.com",
        "sentinel-cogs.s3.amazonaws.com"
    }
    if p.scheme != "https" or not allowed:
        raise SourceError("Satellite asset URL is not from an approved public data host")
    return url

def _asset(item, name):
    data = item.get("assets", {}).get(name)
    if not isinstance(data, dict) or not data.get("href"):
        raise SourceError("Selected scene lacks required asset: " + name)
    return _safe_asset_url(data["href"]), data

def _pixel(url, lon, lat):
    url = _safe_asset_url(url)
    try:
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
            GDAL_HTTP_CONNECTTIMEOUT="8",
            GDAL_HTTP_TIMEOUT="18",
            GDAL_HTTP_MAX_RETRY="1",
            GDAL_HTTP_RETRY_DELAY="1",
            VSI_CACHE="TRUE",
            VSI_CACHE_SIZE="1048576",
        ):
            with rasterio.open(url) as src:
                x, y = transform("EPSG:4326", src.crs, [lon], [lat])
                row, col = src.index(x[0], y[0])
                if row < 0 or col < 0 or row >= src.height or col >= src.width:
                    raise SourceError("Location lies outside the selected satellite tile")
                val = src.read(1, window=Window(col, row, 1, 1), masked=True)
                if val.mask is not np.ma.nomask and np.any(val.mask):
                    raise SourceError("Satellite pixel is masked/nodata")
                result = float(val[0,0])
                if not np.isfinite(result):
                    raise SourceError("Satellite pixel has no finite data")
                return result
    except (rasterio.errors.RasterioError, OSError, ValueError) as exc:
        raise SourceError("Unable to read satellite pixel from public COG") from exc

@lru_cache(maxsize=128)
def _find_scenes(lon_rounded, lat_rounded, date_str):
    lon, lat = lon_rounded, lat_rounded
    day = date.fromisoformat(date_str)
    from_day = day - timedelta(days=45)
    # Searching up to today avoids future data requests.
    to_day = min(date.today(), day + timedelta(days=45))
    if from_day > to_day:
        return ()
    body = {
        "collections": ["sentinel-2-l2a"],
        "intersects": {"type": "Point", "coordinates": [lon, lat]},
        "datetime": from_day.isoformat() + "T00:00:00Z/" + to_day.isoformat() + "T23:59:59Z",
        "limit": 100,
        "query": {"eo:cloud_cover": {"lte": 80}}
    }
    try:
        response = requests.post(STAC_URL, json=body, timeout=18)
        response.raise_for_status()
        items = response.json().get("features", [])
        if not isinstance(items, list):
            raise SourceError("Satellite catalog returned an invalid response")
    except (requests.RequestException, ValueError) as exc:
        raise SourceError("Public satellite catalog is unavailable") from exc
    def rank(item):
        props = item.get("properties", {})
        dt = props.get("datetime", date_str)
        try:
            dist = abs((date.fromisoformat(dt[:10]) - day).days)
        except ValueError:
            dist = 999
        return (dist, float(props.get("eo:cloud_cover") or 100))
    return tuple(sorted(items, key=rank)[:MAX_SCENES])

def _tile_coords(lon, lat, zoom):
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    tx = (lon+180)/360*n
    ty = (1 - asinh(tan(radians(lat)))/pi)/2*n
    ix, iy = int(floor(tx)), int(floor(ty))
    return ix, iy, int((tx-ix)*256), int((ty-iy)*256)

@lru_cache(maxsize=64)
def _terrain_tile(z, x, y):
    url = f"{TERRAIN_BASE}/{z}/{x}/{y}.png"
    try:
        r = requests.get(url, timeout=14)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        arr = np.asarray(img, dtype=np.float64)
        if arr.shape[:2] != (256, 256):
            raise SourceError("Terrain tile has an unexpected size")
        return arr
    except (requests.RequestException, OSError) as exc:
        raise SourceError("Public terrain tiles are unavailable") from exc

def terrain_at(lon, lat):
    z=13
    x,y,px,py=_tile_coords(lon,lat,z)
    tile=_terrain_tile(z,x,y)
    def elev(dx,dy):
        xx, yy = px+dx, py+dy
        if xx<0 or xx>=256 or yy<0 or yy>=256:
            adjacent=_terrain_tile(z,x+(-1 if xx<0 else 1 if xx>=256 else 0),
                                    y+(-1 if yy<0 else 1 if yy>=256 else 0))
            arr=adjacent[yy%256,xx%256]
        else:
            arr=tile[yy,xx]
        return float(arr[0]*256 + arr[1] + arr[2]/256 - 32768)
    centre=elev(0,0)
    # Web Mercator ground resolution approximates actual horizontal distance.
    ground_m=cos(radians(lat))*2*pi*6378137/(256*2**z)
    dx=(elev(1,0)-elev(-1,0))/(2*ground_m)
    dy=(elev(0,1)-elev(0,-1))/(2*ground_m)
    slope=degrees(atan((dx*dx+dy*dy)**0.5))
    return {"elevation":round(centre,3),"slope":round(slope,3)}

def satellite_features(lon, lat, date_str):
    items = _find_scenes(round(lon,5), round(lat,5), date_str)
    if not items:
        raise SourceError("No Sentinel-2 scenes found within 45 days of the requested date")
    reasons=[]
    for item in items:
        try:
            scl_url,_=_asset(item,"scl")
            scl=int(round(_pixel(scl_url,lon,lat)))
            if scl not in CLEAR_SCL:
                reasons.append("SCL class "+str(scl))
                continue
            bands={}
            for name, key in BAND_ASSETS.items():
                url, asset=_asset(item,key)
                raw=_pixel(url,lon,lat)
                # The public Earth Search L2A COGs normally store scaled
                # reflectance uint16. Refuse suspicious values to avoid fake
                # scientific results or unsupported offset assumptions.
                if raw > 1:
                    value=raw/10000.0
                else:
                    value=raw
                if not (0 <= value <= 1):
                    raise SourceError("Reflectance outside valid range: "+name)
                bands[name]=round(value,7)
            # DEM is a public global terrain source; it is not SRTMGL1_003
            # used in training. Disclose this source mismatch in API response.
            elevation=terrain_at(lon,lat)
            props=item.get("properties",{})
            return {**bands, **elevation},{
                "scene_id":item.get("id"),
                "acquired_at":props.get("datetime"),
                "scene_cloud_cover_pct":props.get("eo:cloud_cover"),
                "scl_class_at_point":scl,
                "spectral_source":"Element 84 Earth Search STAC / Sentinel-2 L2A COG",
                "terrain_source":"Mapzen/Tilezen AWS Terrarium global terrain tiles",
                "search_window_days":45
            }
        except SourceError as exc:
            reasons.append(str(exc))
            continue
    raise SourceError("No usable cloud-free satellite pixel among candidate scenes ("+
                      "; ".join(sorted(set(reasons))[:3])+")")
