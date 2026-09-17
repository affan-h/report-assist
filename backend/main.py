import os, logging
import click
import uvicorn
from pythonjsonlogger import jsonlogger

from core.config import default_config

central_log_dir = default_config.CENTRAL_LOG_DIR
os.makedirs(central_log_dir, exist_ok=True)
central_log_path = os.path.join(central_log_dir, default_config.CENTRAL_LOG_FILENAME)

# 1. Get the new central logger by name
central_logger = logging.getLogger(default_config.CENTRAL_LOG_NAME)
central_logger.setLevel(logging.INFO)

# 2. Prevent logs from bubbling up to the root logger
central_logger.propagate = False

# 3. Create the file handler for the central log
#    (Use 'a' for append mode)
c_handler = logging.FileHandler(central_log_path, mode='a')
c_handler.setLevel(logging.INFO)

# 4. Create a formatter
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
)
c_handler.setFormatter(formatter)

# 5. Add the handler *only* to this logger
#    (The 'if' check prevents adding duplicate handlers during a hot-reload in development)
if not central_logger.handlers:
    central_logger.addHandler(c_handler)

@click.command()
@click.option(
    "--env",
    type=click.Choice(["local", "dev", "prod"], case_sensitive=False),
    default="local",
)
@click.option(
    "--debug",
    type=click.BOOL,
    is_flag=True,
    default=False,
)
def main(env: str, debug: bool):
    os.environ["ENV"] = env
    os.environ["DEBUG"] = str(debug)
    uvicorn.run(
        app="app.server:app",
        host=default_config.APP_HOST,
        port=default_config.APP_PORT,
        reload=True if default_config.ENV != "production" else False,
        workers=1,
        log_config=None
    )


if __name__ == "__main__":
    main()
