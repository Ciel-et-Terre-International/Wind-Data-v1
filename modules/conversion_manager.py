# conversion_manager.py

def apply_10min_equivalent(ws, source):
    """
    Applique un facteur de conversion pour ramener la vitesse du vent moyenne
    à une base 10 minutes, selon la source.

    Args:
        ws (float or pd.Series): Vitesse moyenne d'origine (en m/s)
        source (str): Nom de la source (ex: 'era5', 'openmeteo', 'meteostat', 'noaa', etc.)

    Returns:
        float or pd.Series: Vitesse moyenne ramenée à une équivalence 10 minutes
    """

    # Sources déjà en 10 min — pas de correction
    if source in ["meteostat", "noaa"]:
        return ws

    # Sources horaires (modélisées) — correction conservatrice : ×1.10
    if source in ["era5", "nasa_power", "openmeteo"]:
        return ws * 1.10

    # Cas inconnu : pas de correction appliquée
    return ws
