from app.routes.gmail import router as gmail_router
from app.routes.health import router as health_router
from app.routes.intake import router as intake_router
from app.routes.orders import router as orders_router
from app.routes.reviews import router as reviews_router
from app.routes.runs import router as runs_router

ROUTERS = (
    health_router,
    gmail_router,
    intake_router,
    runs_router,
    orders_router,
    reviews_router,
)
