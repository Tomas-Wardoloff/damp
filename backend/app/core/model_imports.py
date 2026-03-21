# Import models so SQLAlchemy metadata includes every table.
from app.modules.collar.models import Collar  # noqa: F401
from app.modules.cow.models import Cow  # noqa: F401
from app.modules.health.models import HealthAnalysis  # noqa: F401
from app.modules.reading.models import Reading  # noqa: F401
