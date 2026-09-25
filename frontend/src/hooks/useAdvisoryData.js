// ---------------------------------------------------------------------------
// useAdvisoryData.js – single fetch of advisory_pixels.geojson, shared across
// Advisory and Research tabs via a simple module-level cache.
// ---------------------------------------------------------------------------
import { useEffect, useState } from 'react';
import { parseGeoJSON, bool, number } from '../helpers';

let _cache = null;  // module-level singleton so re-mounts don't refetch

export function useAdvisoryData() {
  const [features, setFeatures] = useState(_cache || []);
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(!_cache);

  useEffect(() => {
    if (_cache) return;          // already fetched
    setLoading(true);
    fetch('/advisory_pixels.geojson')
      .then((r) => {
        if (!r.ok) throw new Error('Pixel publication file is not available yet.');
        return r.json();
      })
      .then((geo) => {
        const rows = parseGeoJSON(geo)
          .filter((r) => bool(r.environmental_support));
        _cache = rows;
        setFeatures(rows);
        setLoading(false);
      })
      .catch((e) => {
        setLoadError(e.message);
        setLoading(false);
      });
  }, []);

  return { features, loadError, loading };
}

/**
 * Derive sorted unique values for Region (province), District, Palika
 * from the pixel dataset, filtered to only pixels with environmental_support.
 *
 * Field mappings (confirmed from advisory_pixels.csv):
 *   region   → province
 *   district → district
 *   palika   → palika
 */
export function useGeographyOptions(features, region, district) {
  const regions = [...new Set(features.map((r) => r.province).filter(Boolean))].sort();

  const districts = [...new Set(
    features
      .filter((r) => !region || r.province === region)
      .map((r) => r.district)
      .filter(Boolean)
  )].sort();

  const palikas = [...new Set(
    features
      .filter((r) =>
        (!region || r.province === region) &&
        (!district || r.district === district)
      )
      .map((r) => r.palika)
      .filter(Boolean)
  )].sort();

  return { regions, districts, palikas };
}

/**
 * Filter and compute a bounding box for the given geography selection.
 * Returns { filtered, bounds } where bounds is [[minLat, minLon], [maxLat, maxLon]]
 * or null when there's nothing to bound.
 */
export function useFilteredPixels(features, { region, district, palika }) {
  const filtered = features.filter((r) => {
    if (region && r.province !== region) return false;
    if (district && r.district !== district) return false;
    if (palika && r.palika !== palika) return false;
    return true;
  });

  let bounds = null;
  if (filtered.length) {
    let minLat = Infinity, maxLat = -Infinity, minLon = Infinity, maxLon = -Infinity;
    for (const r of filtered) {
      const la = number(r.lat), lo = number(r.lon);
      if (la !== null && lo !== null) {
        if (la < minLat) minLat = la;
        if (la > maxLat) maxLat = la;
        if (lo < minLon) minLon = lo;
        if (lo > maxLon) maxLon = lo;
      }
    }
    if (Number.isFinite(minLat)) {
      bounds = [[minLat, minLon], [maxLat, maxLon]];
    }
  }

  return { filtered, bounds };
}
