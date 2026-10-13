"""Create or update the "Effectif GRH" dashboard (see build_dashboards.py for the full suite)."""
from build_dashboards import main

if __name__ == "__main__":
    main(["--only", "effectif"])
