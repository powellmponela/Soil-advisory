import pandas as pd
from .config import PUBLIC_PREDICTIONS, PRIVATE_AREAS

PUBLIC_COLUMNS = [
    "district","municipality","crop","season","scenario",
    "yield_predicted_t_ha","n_rate_kg_ha","ae_n_kg_grain_per_kg_n",
    "pfp_n_kg_grain_per_kg_n","n_reduction_kg_ha",
    "prediction_lower_t_ha","prediction_upper_t_ha","model_version","published_version",
]

def load_public_predictions() -> pd.DataFrame:
    if not PUBLIC_PREDICTIONS.exists():
        return pd.DataFrame(columns=PUBLIC_COLUMNS)
    df = pd.read_csv(PUBLIC_PREDICTIONS)
    missing=[c for c in PUBLIC_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Published prediction file is missing columns: {missing}")
    return df[PUBLIC_COLUMNS].copy()

def safe_private_listing(area: str, relative_path: str="") -> list[dict]:
    if area not in PRIVATE_AREAS:
        raise ValueError("Unknown private area")
    root=PRIVATE_AREAS[area].resolve()
    target=(root/relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path escapes private area") from exc
    if not target.exists(): return []
    if not target.is_dir(): raise ValueError("Target is not a directory")
    entries=[]
    for p in sorted(target.iterdir(),key=lambda x:(not x.is_dir(),x.name.lower())):
        stat=p.stat()
        entries.append({"name":p.name,"type":"folder" if p.is_dir() else "file",
          "size_bytes":None if p.is_dir() else stat.st_size,
          "relative_path":str(p.relative_to(root)).replace("\\","/")})
    return entries
