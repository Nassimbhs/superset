"""Push theme/grh_modern.css to Superset without rebuilding charts.

Updates the 'GRH moderne' CSS template and the CSS of every dashboard in grh_ids.json.
Usage: python apply_theme.py
"""
import grh_builder
from superset_client import SupersetClient


def main() -> None:
    client = SupersetClient()
    print(f"css template '{grh_builder.THEME_NAME}': id={grh_builder.upsert_css_template(client)}")
    css = grh_builder.theme_css()
    for key, info in grh_builder.load_ids().items():
        client.put(f"/api/v1/dashboard/{info['dashboard']}", {"css": css})
        print(f"  {key}: {client.url}/superset/dashboard/{info['slug']}/")


if __name__ == "__main__":
    main()
