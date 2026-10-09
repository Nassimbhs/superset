# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os

from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache

logger = logging.getLogger()

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

SQLALCHEMY_EXAMPLES_URI = (
    f"{DATABASE_DIALECT}://"
    f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
    f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Extra categorical palettes (shown under "Custom" in chart/dashboard color pickers).
# Pick them in Explore → Customize → Color Scheme, or Dashboard → Edit properties → Colors.
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "corporateBlue",
        "description": "Professional blues and neutrals",
        "label": "Corporate Blue",
        "colors": [
            "#0B3D91", "#1E88E5", "#42A5F5", "#90CAF9", "#546E7A", "#78909C",
            "#B0BEC5", "#263238", "#00897B", "#26A69A", "#80CBC4", "#FF8F00",
        ],
    },
    {
        "id": "vibrantDashboard",
        "description": "High-contrast colors for dashboards",
        "label": "Vibrant Dashboard",
        "colors": [
            "#E53935", "#FB8C00", "#FDD835", "#43A047", "#00ACC1", "#1E88E5",
            "#8E24AA", "#D81B60", "#6D4C41", "#546E7A", "#EF5350", "#FFA726",
            "#FFEE58", "#66BB6A", "#26C6DA", "#42A5F5",
        ],
    },
    {
        "id": "pastelSoft",
        "description": "Soft pastels for light backgrounds",
        "label": "Pastel Soft",
        "colors": [
            "#A5D6A7", "#81D4FA", "#CE93D8", "#FFCC80", "#EF9A9A", "#80CBC4",
            "#FFF59D", "#B39DDB", "#90CAF9", "#F48FB1", "#BCAAA4", "#B0BEC5",
        ],
    },
    {
        "id": "earthTones",
        "description": "Natural earth and forest tones",
        "label": "Earth Tones",
        "colors": [
            "#5D4037", "#8D6E63", "#A1887F", "#6D4C41", "#558B2F", "#7CB342",
            "#9E9D24", "#F9A825", "#EF6C00", "#BF360C", "#795548", "#A1887F",
        ],
    },
    {
        "id": "tunisiaBrand",
        "description": "Red / white / gold inspired palette",
        "label": "Tunisia Brand",
        "colors": [
            "#E31C23", "#C62828", "#FFFFFF", "#F5F5F5", "#B71C1C", "#FFD54F",
            "#FFC107", "#37474F", "#607D8B", "#90A4AE", "#D32F2F", "#FFECB3",
        ],
    },
    {
        "id": "colorblindSafe",
        "description": "Wong palette — colorblind-friendly",
        "label": "Colorblind Safe",
        "colors": [
            "#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2",
            "#D55E00", "#CC79A7", "#999999", "#44AA99", "#882255", "#117733",
        ],
    },
    {
        "id": "oceanDepths",
        "description": "Deep sea blues and aquas",
        "label": "Ocean Depths",
        "colors": [
            "#012A4A", "#013A63", "#01497C", "#014F86", "#2A6F97", "#2C7DA0",
            "#468FAF", "#61A5C2", "#89C2D9", "#A9D6E5", "#00B4D8", "#48CAE4",
        ],
    },
    {
        "id": "berryPunch",
        "description": "Berry and magenta tones",
        "label": "Berry Punch",
        "colors": [
            "#4A0E4E", "#810955", "#C62E65", "#F05A7E", "#FF8FAB", "#9B1D5A",
            "#6A0572", "#AB83A1", "#D4A5A5", "#E8B4B8", "#C9184A", "#FF4D6D",
        ],
    },
    {
        "id": "citrusFresh",
        "description": "Lime, lemon and orange accents",
        "label": "Citrus Fresh",
        "colors": [
            "#FF6B00", "#FF8500", "#FF9E00", "#FFB700", "#FFD000", "#FFEA00",
            "#AACC00", "#80B918", "#55A630", "#2B9348", "#007F5F", "#D4D700",
        ],
    },
    {
        "id": "nordicFrost",
        "description": "Cool Nordic greys and icy blues",
        "label": "Nordic Frost",
        "colors": [
            "#2E3440", "#3B4252", "#434C5E", "#4C566A", "#D8DEE9", "#E5E9F0",
            "#ECEFF4", "#8FBCBB", "#88C0D0", "#81A1C1", "#5E81AC", "#B48EAD",
        ],
    },
    {
        "id": "mediterranean",
        "description": "Sun, sea and terracotta",
        "label": "Mediterranean",
        "colors": [
            "#1A535C", "#4ECDC4", "#F7FFF7", "#FF6B6B", "#FFE66D", "#2C3E50",
            "#E67E22", "#3498DB", "#27AE60", "#9B59B6", "#E74C3C", "#F39C12",
        ],
    },
    {
        "id": "neonNights",
        "description": "Neon accents for dark dashboards",
        "label": "Neon Nights",
        "colors": [
            "#FF00FF", "#00FFFF", "#39FF14", "#FF073A", "#FFF700", "#FF6EC7",
            "#00F5FF", "#7DF9FF", "#FE4164", "#CCFF00", "#FF5F1F", "#BF00FF",
        ],
    },
    {
        "id": "monochromeBlue",
        "description": "Single-hue blue scale as categories",
        "label": "Monochrome Blue",
        "colors": [
            "#E3F2FD", "#BBDEFB", "#90CAF9", "#64B5F6", "#42A5F5", "#2196F3",
            "#1E88E5", "#1976D2", "#1565C0", "#0D47A1", "#82B1FF", "#448AFF",
        ],
    },
    {
        "id": "monochromeGreen",
        "description": "Single-hue green scale as categories",
        "label": "Monochrome Green",
        "colors": [
            "#E8F5E9", "#C8E6C9", "#A5D6A7", "#81C784", "#66BB6A", "#4CAF50",
            "#43A047", "#388E3C", "#2E7D32", "#1B5E20", "#B9F6CA", "#69F0AE",
        ],
    },
    {
        "id": "jewelTones",
        "description": "Rich gemstone colors",
        "label": "Jewel Tones",
        "colors": [
            "#0D7377", "#14919B", "#9B2226", "#AE2012", "#BB3E03", "#CA6702",
            "#5E2BFF", "#C77DFF", "#006466", "#065A60", "#7B2CBF", "#9D4EDD",
        ],
    },
    {
        "id": "safari",
        "description": "Savanna golds and greens",
        "label": "Safari",
        "colors": [
            "#582F0E", "#7F4F24", "#936639", "#A68A64", "#B6AD90", "#C2C5AA",
            "#A4AC86", "#656D4A", "#414833", "#333D29", "#D4A373", "#CCD5AE",
        ],
    },
    {
        "id": "candyShop",
        "description": "Bright candy-like colors",
        "label": "Candy Shop",
        "colors": [
            "#FF6B6B", "#FF8E72", "#FFA07A", "#FFD93D", "#6BCB77", "#4D96FF",
            "#9B5DE5", "#F15BB5", "#00BBF9", "#00F5D4", "#FEE440", "#F72585",
        ],
    },
    {
        "id": "slateMetro",
        "description": "Urban slate and metro accents",
        "label": "Slate Metro",
        "colors": [
            "#212529", "#343A40", "#495057", "#6C757D", "#ADB5BD", "#CED4DA",
            "#0D6EFD", "#198754", "#DC3545", "#FD7E14", "#FFC107", "#20C997",
        ],
    },
    {
        "id": "vintagePrint",
        "description": "Muted vintage print colors",
        "label": "Vintage Print",
        "colors": [
            "#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51", "#6D6875",
            "#B5838D", "#E5989B", "#FFB4A2", "#FFCDB2", "#457B9D", "#A8DADC",
        ],
    },
    {
        "id": "arcticAurora",
        "description": "Aurora borealis inspired",
        "label": "Arctic Aurora",
        "colors": [
            "#0B132B", "#1C2541", "#3A506B", "#5BC0BE", "#6FFFE9", "#7B2CBF",
            "#9D4EDD", "#C77DFF", "#E0AAFF", "#00F5D4", "#80FFDB", "#7400B8",
        ],
    },
    {
        "id": "desertBloom",
        "description": "Sand, clay and cactus blooms",
        "label": "Desert Bloom",
        "colors": [
            "#E07A5F", "#3D405B", "#81B29A", "#F2CC8F", "#F4F1DE", "#D4A373",
            "#BC6C25", "#DDA15E", "#FEFAE0", "#606C38", "#283618", "#A3B18A",
        ],
    },
    {
        "id": "techStack",
        "description": "Modern tech / SaaS dashboard look",
        "label": "Tech Stack",
        "colors": [
            "#6366F1", "#8B5CF6", "#A855F7", "#EC4899", "#F43F5E", "#F97316",
            "#EAB308", "#22C55E", "#14B8A6", "#06B6D4", "#3B82F6", "#64748B",
        ],
    },
    {
        "id": "financeNavy",
        "description": "Banking navy, gold and teal",
        "label": "Finance Navy",
        "colors": [
            "#0A2540", "#1B3A5F", "#2C5282", "#C9A227", "#D4AF37", "#F0E6C8",
            "#0D9488", "#14B8A6", "#5EEAD4", "#334155", "#64748B", "#94A3B8",
        ],
    },
    {
        "id": "healthcareClean",
        "description": "Clean medical blues and greens",
        "label": "Healthcare Clean",
        "colors": [
            "#0077B6", "#00B4D8", "#90E0EF", "#CAF0F8", "#2A9D8F", "#52B788",
            "#95D5B2", "#B7E4C7", "#023E8A", "#48CAE4", "#76C893", "#D8F3DC",
        ],
    },
    {
        "id": "retailPop",
        "description": "Retail / e-commerce pop colors",
        "label": "Retail Pop",
        "colors": [
            "#FF006E", "#FB5607", "#FFBE0B", "#8338EC", "#3A86FF", "#06D6A0",
            "#EF476F", "#FFD166", "#118AB2", "#073B4C", "#F72585", "#7209B7",
        ],
    },
    {
        "id": "graphiteAccent",
        "description": "Graphite with colorful accents",
        "label": "Graphite Accent",
        "colors": [
            "#1C1C1C", "#2D2D2D", "#404040", "#595959", "#737373", "#E63946",
            "#F4A261", "#2A9D8F", "#457B9D", "#E9C46A", "#A8DADC", "#F1FAEE",
        ],
    },
    {
        "id": "tropicLagoon",
        "description": "Tropical lagoon turquoise and coral",
        "label": "Tropic Lagoon",
        "colors": [
            "#006D77", "#83C5BE", "#EDF6F9", "#FFDDD2", "#E29578", "#00A896",
            "#02C39A", "#F0F3BD", "#028090", "#00B4D8", "#FF9F1C", "#FFBF69",
        ],
    },
    {
        "id": "royalCourt",
        "description": "Royal purple, gold and crimson",
        "label": "Royal Court",
        "colors": [
            "#240046", "#3C096C", "#5A189A", "#7B2CBF", "#9D4EDD", "#C77DFF",
            "#FFD700", "#DAA520", "#B8860B", "#8B0000", "#A52A2A", "#CD5C5C",
        ],
    },
    {
        "id": "inkAndWash",
        "description": "Ink wash blacks and soft washes",
        "label": "Ink And Wash",
        "colors": [
            "#0D0D0D", "#1A1A1A", "#333333", "#4D4D4D", "#808080", "#B3B3B3",
            "#D9D9D9", "#5C6BC0", "#7986CB", "#9FA8DA", "#C5CAE9", "#E8EAF6",
        ],
    },
    {
        "id": "harvestFestival",
        "description": "Autumn harvest oranges and reds",
        "label": "Harvest Festival",
        "colors": [
            "#6A040F", "#9D0208", "#D00000", "#DC2F02", "#E85D04", "#F48C06",
            "#FAA307", "#FFBA08", "#370617", "#03071E", "#E36414", "#9A031E",
        ],
    },
    {
        "id": "springMeadow",
        "description": "Fresh spring meadow greens",
        "label": "Spring Meadow",
        "colors": [
            "#D8F3DC", "#B7E4C7", "#95D5B2", "#74C69D", "#52B788", "#40916C",
            "#2D6A4F", "#1B4332", "#081C15", "#A3D977", "#70E000", "#38B000",
        ],
    },
    {
        "id": "steelCopper",
        "description": "Industrial steel and copper",
        "label": "Steel Copper",
        "colors": [
            "#0F172A", "#1E293B", "#334155", "#475569", "#64748B", "#94A3B8",
            "#B45309", "#D97706", "#F59E0B", "#FBBF24", "#CD7F32", "#B87333",
        ],
    },
    {
        "id": "lavenderFields",
        "description": "Lavender and soft purple fields",
        "label": "Lavender Fields",
        "colors": [
            "#F8F1FF", "#EBD9FC", "#D4B3F8", "#B98CF0", "#9B5DE5", "#7B2CBF",
            "#5A189A", "#3C096C", "#CDB4DB", "#FFC8DD", "#FFAFCC", "#BDE0FE",
        ],
    },
    {
        "id": "tableauClassic",
        "description": "Classic Tableau-like categorical set",
        "label": "Tableau Classic",
        "colors": [
            "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948",
            "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC", "#86BCB6", "#D37295",
        ],
    },
    {
        "id": "powerBiDefault",
        "description": "Power BI inspired categorical set",
        "label": "Power BI Inspired",
        "colors": [
            "#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2",
            "#D9B300", "#D64550", "#197278", "#1AAB40", "#15C6F4", "#F2C80F",
        ],
    },
    {
        "id": "tolBright",
        "description": "Paul Tol bright qualitative",
        "label": "Tol Bright",
        "colors": [
            "#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377",
            "#BBBBBB", "#000000", "#44AA99", "#882255", "#DDCC77", "#332288",
        ],
    },
]

# Extra sequential / diverging palettes (heatmaps, country maps, etc.).
EXTRA_SEQUENTIAL_COLOR_SCHEMES = [
    {
        "id": "coolWarm",
        "description": "Cool to warm diverging",
        "label": "Cool / Warm",
        "isDiverging": True,
        "colors": [
            "#2166AC", "#67A9CF", "#D1E5F0", "#F7F7F7", "#FDDBC7", "#EF8A62", "#B2182B",
        ],
    },
    {
        "id": "tealOrange",
        "description": "Teal to orange diverging",
        "label": "Teal / Orange",
        "isDiverging": True,
        "colors": [
            "#01665E", "#5AB4AC", "#C7EAE5", "#F5F5F5", "#F6E8C3", "#D8B365", "#8C510A",
        ],
    },
    {
        "id": "midnightBlue",
        "description": "Deep midnight sequential blues",
        "label": "Midnight Blue",
        "colors": [
            "#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6",
            "#4292C6", "#2171B5", "#08519C", "#08306B",
        ],
    },
    {
        "id": "sunsetHeat",
        "description": "Yellow to deep red heat map",
        "label": "Sunset Heat",
        "colors": [
            "#FFFFCC", "#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C",
            "#FC4E2A", "#E31A1C", "#BD0026", "#800026",
        ],
    },
    {
        "id": "forestDensity",
        "description": "Light to dense greens",
        "label": "Forest Density",
        "colors": [
            "#F7FCF5", "#E5F5E0", "#C7E9C0", "#A1D99B", "#74C476",
            "#41AB5D", "#238B45", "#006D2C", "#00441B",
        ],
    },
    {
        "id": "plasmaGlow",
        "description": "Purple-pink-yellow plasma glow",
        "label": "Plasma Glow",
        "colors": [
            "#0D0887", "#5B02A3", "#9A179B", "#CB4678", "#EB7852",
            "#FBB32F", "#F0F921",
        ],
    },
    {
        "id": "cividisLike",
        "description": "Colorblind-friendly blue-yellow",
        "label": "Cividis Like",
        "colors": [
            "#00204C", "#213D6B", "#555B6E", "#7B7A77", "#A59C74",
            "#D3C065", "#FFE945",
        ],
    },
    {
        "id": "iceToFire",
        "description": "Ice blue through white to fire red",
        "label": "Ice To Fire",
        "isDiverging": True,
        "colors": [
            "#053061", "#2166AC", "#4393C3", "#92C5DE", "#D1E5F0",
            "#F7F7F7", "#FDDBC7", "#F4A582", "#D6604D", "#B2182B", "#67001F",
        ],
    },
    {
        "id": "roseQuartz",
        "description": "Soft rose sequential",
        "label": "Rose Quartz",
        "colors": [
            "#FFF0F3", "#FFCCD5", "#FF8FA3", "#FF4D6D", "#C9184A",
            "#A4133C", "#800F2F", "#590D22",
        ],
    },
    {
        "id": "amberDepth",
        "description": "Light cream to deep amber",
        "label": "Amber Depth",
        "colors": [
            "#FFFBEB", "#FEF3C7", "#FDE68A", "#FCD34D", "#FBBF24",
            "#F59E0B", "#D97706", "#B45309", "#92400E", "#78350F",
        ],
    },
    {
        "id": "indigoNight",
        "description": "Pale indigo to night",
        "label": "Indigo Night",
        "colors": [
            "#EEF2FF", "#E0E7FF", "#C7D2FE", "#A5B4FC", "#818CF8",
            "#6366F1", "#4F46E5", "#4338CA", "#3730A3", "#312E81",
        ],
    },
    {
        "id": "mintCream",
        "description": "Mint cream to deep teal",
        "label": "Mint Cream",
        "colors": [
            "#F0FDFA", "#CCFBF1", "#99F6E4", "#5EEAD4", "#2DD4BF",
            "#14B8A6", "#0D9488", "#0F766E", "#115E59", "#134E4A",
        ],
    },
    {
        "id": "crimsonFade",
        "description": "White to deep crimson",
        "label": "Crimson Fade",
        "colors": [
            "#FFF5F5", "#FED7D7", "#FEB2B2", "#FC8181", "#F56565",
            "#E53E3E", "#C53030", "#9B2C2C", "#742A2A",
        ],
    },
    {
        "id": "sandToSea",
        "description": "Sand yellow to deep sea",
        "label": "Sand To Sea",
        "isDiverging": True,
        "colors": [
            "#F4A261", "#E9C46A", "#F5F5F5", "#2A9D8F", "#264653",
        ],
    },
    {
        "id": "violetBloom",
        "description": "Lavender to deep violet",
        "label": "Violet Bloom",
        "colors": [
            "#FAF5FF", "#F3E8FF", "#E9D5FF", "#D8B4FE", "#C084FC",
            "#A855F7", "#9333EA", "#7E22CE", "#6B21A8", "#581C87",
        ],
    },
    {
        "id": "copperRust",
        "description": "Pale peach to copper rust",
        "label": "Copper Rust",
        "colors": [
            "#FFF7ED", "#FFEDD5", "#FED7AA", "#FDBA74", "#FB923C",
            "#F97316", "#EA580C", "#C2410C", "#9A3412", "#7C2D12",
        ],
    },
    {
        "id": "slateDepth",
        "description": "Light slate to charcoal",
        "label": "Slate Depth",
        "colors": [
            "#F8FAFC", "#F1F5F9", "#E2E8F0", "#CBD5E1", "#94A3B8",
            "#64748B", "#475569", "#334155", "#1E293B", "#0F172A",
        ],
    },
    {
        "id": "emeraldPulse",
        "description": "Pale emerald to forest",
        "label": "Emerald Pulse",
        "colors": [
            "#ECFDF5", "#D1FAE5", "#A7F3D0", "#6EE7B7", "#34D399",
            "#10B981", "#059669", "#047857", "#065F46", "#064E3B",
        ],
    },
    {
        "id": "magentaWave",
        "description": "Pink magenta sequential",
        "label": "Magenta Wave",
        "colors": [
            "#FDF2F8", "#FCE7F3", "#FBCFE8", "#F9A8D4", "#F472B6",
            "#EC4899", "#DB2777", "#BE185D", "#9D174D", "#831843",
        ],
    },
    {
        "id": "skyHorizon",
        "description": "Horizon sky cyan to navy",
        "label": "Sky Horizon",
        "colors": [
            "#ECFEFF", "#CFFAFE", "#A5F3FC", "#67E8F9", "#22D3EE",
            "#06B6D4", "#0891B2", "#0E7490", "#155E75", "#164E63",
        ],
    },
    {
        "id": "oliveGrove",
        "description": "Pale olive to deep olive",
        "label": "Olive Grove",
        "colors": [
            "#F7FEE7", "#ECFCCB", "#D9F99D", "#BEF264", "#A3E635",
            "#84CC16", "#65A30D", "#4D7C0F", "#3F6212", "#365314",
        ],
    },
    {
        "id": "wineCellar",
        "description": "Blush to deep wine",
        "label": "Wine Cellar",
        "colors": [
            "#FFF1F2", "#FFE4E6", "#FECDD3", "#FDA4AF", "#FB7185",
            "#F43F5E", "#E11D48", "#BE123C", "#9F1239", "#881337",
        ],
    },
    {
        "id": "peachToPlum",
        "description": "Peach through white to plum",
        "label": "Peach To Plum",
        "isDiverging": True,
        "colors": [
            "#FF8A65", "#FFAB91", "#FFCCBC", "#FBE9E7", "#F3E5F5",
            "#E1BEE7", "#CE93D8", "#AB47BC", "#8E24AA",
        ],
    },
    {
        "id": "fogToStorm",
        "description": "Fog grey to storm blue",
        "label": "Fog To Storm",
        "colors": [
            "#F5F7FA", "#E4E7EB", "#CBD2D9", "#9AA5B1", "#7B8794",
            "#52606D", "#3E4C59", "#323F4B", "#1F2933", "#0B1D36",
        ],
    },
]

# Default UI language: French
BABEL_DEFAULT_LOCALE = "fr"
LANGUAGES = {
    "fr": {"flag": "fr", "name": "French"},
    "en": {"flag": "us", "name": "English"},
}


def FLASK_APP_MUTATOR(app):  # noqa: N802
    # FAB's /lang/<locale> redirects using its session "page_history", which is
    # only filled by classic FAB views (e.g. /users/list/), not by React pages.
    from urllib.parse import urlparse

    from flask import abort, redirect, request, session
    from flask_babel import refresh

    def change_locale(locale):
        if locale not in app.appbuilder.bm.languages:
            abort(404, description="Locale not supported.")
        session["locale"] = locale
        refresh()
        target = "/"
        referrer = request.referrer
        if referrer:
            parsed = urlparse(referrer)
            if parsed.netloc == request.host and not parsed.path.startswith("/lang/"):
                target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        return redirect(target)

    if "LocaleView.index" in app.view_functions:
        app.view_functions["LocaleView.index"] = change_locale
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
WEBDRIVER_BASEURL = "http://superset:8088/"  # When using docker compose baseurl should be http://superset_app:8088/
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL
SQLLAB_CTAS_NO_LIMIT = True

#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at " f"[{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")

