import math
import os

import plotly.graph_objects as go


def _format_site_hover(site):
    """
    Construit le texte d'infobulle pour un site.
    """
    name = site.get("name", "")
    ref = site.get("reference", "")
    country = site.get("country", "")
    lat = site.get("latitude", None)
    lon = site.get("longitude", None)
    start = site.get("start", "")
    end = site.get("end", "")

    coords = ""
    if lat is not None and lon is not None:
        coords = f"({lat:.3f}, {lon:.3f})"

    lines = []
    if ref or name:
        lines.append(f"<b>{ref} – {name}</b>")
    if country:
        lines.append(f"Country: {country}")
    if coords:
        lines.append(f"Coordinates: {coords}")
    if start and end:
        lines.append(f"Period: {start} → {end}")

    return "<br>".join(lines)


def _format_meteostat_hover(site, station_key):
    """
    Construit le texte d'infobulle pour une station Meteostat (station1 / station2).
    """
    st = site.get(station_key) or {}
    if not st:
        return None

    lat = st.get("latitude")
    lon = st.get("longitude")
    if lat is None or lon is None or (isinstance(lat, float) and math.isnan(lat)):
        return None

    name = st.get("name", "")
    sid = st.get("id", "")
    dist = st.get("distance_km", None)
    elev = st.get("elevation", None)

    lines = [f"<b>Meteostat – {station_key}</b>"]
    if name:
        lines.append(f"Name: {name}")
    if sid:
        lines.append(f"ID: {sid}")
    if dist is not None and not (isinstance(dist, float) and math.isnan(dist)):
        lines.append(f"Distance to site: {dist:.1f} km")
    if elev is not None and not (isinstance(elev, float) and math.isnan(elev)):
        lines.append(f"Elevation: {elev:.0f} m")

    site_name = site.get("name", "")
    ref = site.get("reference", "")
    if ref or site_name:
        lines.append(f"Site: {ref} – {site_name}")

    return {
        "lat": float(lat),
        "lon": float(lon),
        "text": "<br>".join(lines),
    }


def _format_noaa_hover(site, key):
    """
    Construit le texte d'infobulle pour une station NOAA (noaa1 / noaa2).
    """
    st = site.get(key) or {}
    if not st:
        return None

    lat = st.get("latitude")
    lon = st.get("longitude")
    if lat is None or lon is None or (isinstance(lat, float) and math.isnan(lat)):
        return None

    name = st.get("name", "")
    station_id = st.get("station_id", "")
    dist = st.get("distance_km", None)
    elev = st.get("elevation_m", None)

    lines = [f"<b>NOAA – {key}</b>"]
    if name:
        lines.append(f"Name: {name}")
    if station_id:
        lines.append(f"Station ID: {station_id}")
    if dist is not None and not (isinstance(dist, float) and math.isnan(dist)):
        lines.append(f"Distance to site: {dist:.1f} km")
    if elev is not None and not (isinstance(elev, float) and math.isnan(elev)):
        lines.append(f"Elevation: {elev:.0f} m")

    site_name = site.get("name", "")
    ref = site.get("reference", "")
    if ref or site_name:
        lines.append(f"Site: {ref} – {site_name}")

    return {
        "lat": float(lat),
        "lon": float(lon),
        "text": "<br>".join(lines),
    }


def _collect_points(sites_data):
    """
    Regroupe les coordonnées et textes pour sites / stations.
    """
    site_lats, site_lons, site_texts = [], [], []
    meteo_lats, meteo_lons, meteo_texts = [], [], []
    noaa_lats, noaa_lons, noaa_texts = [], [], []

    for site in sites_data:
        # Site principal
        lat = site.get("latitude")
        lon = site.get("longitude")
        if lat is not None and lon is not None:
            site_lats.append(float(lat))
            site_lons.append(float(lon))
            site_texts.append(_format_site_hover(site))

        # Stations Meteostat (station1 / station2)
        for station_key in ("meteostat1", "meteostat2"):
            info = _format_meteostat_hover(site, station_key)
            if info is not None:
                meteo_lats.append(info["lat"])
                meteo_lons.append(info["lon"])
                meteo_texts.append(info["text"])

        # Stations NOAA (noaa1 / noaa2)
        for key in ("noaa1", "noaa2"):
            info = _format_noaa_hover(site, key)
            if info is not None:
                noaa_lats.append(info["lat"])
                noaa_lons.append(info["lon"])
                noaa_texts.append(info["text"])

    return (
        site_lats,
        site_lons,
        site_texts,
        meteo_lats,
        meteo_lons,
        meteo_texts,
        noaa_lats,
        noaa_lons,
        noaa_texts,
    )


def _compute_center(site_lats, site_lons):
    """
    Centre approximatif de la carte (moyenne simple des lat/lon des sites).
    """
    if not site_lats or not site_lons:
        return 0.0, 0.0
    return float(sum(site_lats) / len(site_lats)), float(sum(site_lons) / len(site_lons))


def _build_fig_scattergeo(
    site_lats,
    site_lons,
    site_texts,
    meteo_lats,
    meteo_lons,
    meteo_texts,
    noaa_lats,
    noaa_lons,
    noaa_texts,
):
    """
    Version sans Mapbox, fond Natural Earth.
    """
    fig = go.Figure()

    # Sites
    if site_lats:
        fig.add_trace(
            go.Scattergeo(
                lon=site_lons,
                lat=site_lats,
                text=site_texts,
                hoverinfo="text",
                mode="markers",
                name="Sites",
                marker=dict(
                    size=10,
                    symbol="circle",
                    line=dict(width=1, color="black"),
                ),
            )
        )

    # Meteostat
    if meteo_lats:
        fig.add_trace(
            go.Scattergeo(
                lon=meteo_lons,
                lat=meteo_lats,
                text=meteo_texts,
                hoverinfo="text",
                mode="markers",
                name="Meteostat stations",
                marker=dict(
                    size=7,
                    symbol="square",
                    line=dict(width=0.5, color="black"),
                ),
            )
        )

    # NOAA
    if noaa_lats:
        fig.add_trace(
            go.Scattergeo(
                lon=noaa_lons,
                lat=noaa_lats,
                text=noaa_texts,
                hoverinfo="text",
                mode="markers",
                name="NOAA stations",
                marker=dict(
                    size=6,
                    symbol="triangle-up",
                    line=dict(width=0.5, color="black"),
                ),
            )
        )

    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        countrycolor="gray",
        showland=True,
        landcolor="rgb(240, 240, 240)",
        showocean=True,
        oceancolor="rgb(220, 235, 245)",
        showcoastlines=True,
        coastlinecolor="gray",
        lataxis_showgrid=True,
        lonaxis_showgrid=True,
        lataxis_gridcolor="rgba(150,150,150,0.3)",
        lonaxis_gridcolor="rgba(150,150,150,0.3)",
    )

    fig.update_layout(
        title=dict(
            text="Wind Data – Sites & Stations",
            x=0.5,
            xanchor="center",
            y=0.96,
            yanchor="top",
        ),
        legend=dict(
            yanchor="bottom",
            y=0.02,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        template="plotly_white",
    )

    return fig


def _build_fig_mapbox(
    site_lats,
    site_lons,
    site_texts,
    meteo_lats,
    meteo_lons,
    meteo_texts,
    noaa_lats,
    noaa_lons,
    noaa_texts,
    mapbox_token,
):
    """
    Version avec Mapbox (fond satellite).

    Sites      : rouge
    NOAA       : cyan (triangle)
    Meteostat  : magenta (cercle), dessiné en dernier pour apparaître au-dessus.
    """
    center_lat, center_lon = _compute_center(site_lats, site_lons)

    fig = go.Figure()

    # NOAA (on dessine d'abord ce qui peut "cacher")
    if noaa_lats:
        fig.add_trace(
            go.Scattermapbox(
                lon=noaa_lons,
                lat=noaa_lats,
                text=noaa_texts,
                hoverinfo="text",
                mode="markers",
                name="NOAA stations",
                marker=dict(
                    size=9,
                    symbol="triangle",
                    color="cyan",
                ),
            )
        )

    # Sites
    if site_lats:
        fig.add_trace(
            go.Scattermapbox(
                lon=site_lons,
                lat=site_lats,
                text=site_texts,
                hoverinfo="text",
                mode="markers",
                name="Sites",
                marker=dict(
                    size=11,
                    symbol="circle",
                    color="red",
                ),
            )
        )

    # Meteostat – DESSINÉ EN DERNIER
    if meteo_lats:
        fig.add_trace(
            go.Scattermapbox(
                lon=meteo_lons,
                lat=meteo_lats,
                text=meteo_texts,
                hoverinfo="text",
                mode="markers",
                name="Meteostat stations",
                marker=dict(
                    size=13,
                    symbol="circle",
                    color="magenta",  # couleur foncée très visible
                ),
            )
        )

    fig.update_layout(
        mapbox=dict(
            accesstoken=mapbox_token,
            style="satellite-streets",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=4,
        ),
        title=dict(
            text="Wind Data – Sites & Stations (Satellite)",
            x=0.5,
            xanchor="center",
            y=0.96,
            yanchor="top",
        ),
        legend=dict(
            yanchor="bottom",
            y=0.02,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=0, r=0, t=50, b=0),
    )

    return fig




def visualize_sites_plotly(sites_data, output_html_path="visualisation_plotly.html"):
    """
    Génère une visualisation Plotly des sites et stations associés.

    - Si une variable d'environnement MAPBOX_TOKEN est définie :
        → utilise une carte satellite (Scattermapbox / Mapbox).
    - Sinon :
        → utilise la carte 2D Natural Earth (Scattergeo).
    """
    (
        site_lats,
        site_lons,
        site_texts,
        meteo_lats,
        meteo_lons,
        meteo_texts,
        noaa_lats,
        noaa_lons,
        noaa_texts,
    ) = _collect_points(sites_data)

    mapbox_token = os.getenv("MAPBOX_TOKEN", "").strip()

    if mapbox_token:
        print("MAPBOX_TOKEN détecté → utilisation du fond satellite Mapbox.")
        fig = _build_fig_mapbox(
            site_lats,
            site_lons,
            site_texts,
            meteo_lats,
            meteo_lons,
            meteo_texts,
            noaa_lats,
            noaa_lons,
            noaa_texts,
            mapbox_token,
        )
    else:
        print(
            "MAPBOX_TOKEN non défini → utilisation du fond 'Natural Earth' (Scattergeo)."
        )
        fig = _build_fig_scattergeo(
            site_lats,
            site_lons,
            site_texts,
            meteo_lats,
            meteo_lons,
            meteo_texts,
            noaa_lats,
            noaa_lons,
            noaa_texts,
        )

    fig.write_html(output_html_path)
    print(f"Visualisation Plotly générée : {output_html_path}")
