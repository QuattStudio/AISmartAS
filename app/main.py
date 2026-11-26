import sys

from core import constants
from core.logger import logger
from core.paths import project_path
from frontend.app import app as web_app
from vision.camera import camera
from core.metadata import app_meta





def main() -> int:
    
    if not logger.initialize(str(project_path("resources", "logs", "app.log")), userMeta=app_meta):
        print("Logging sub-system failed to initialize!")
        return constants.ExitStatus.FAILURE

    logger.info("WELCOME to AI powered Smart Attendance System")

    try:
        if not camera.open():
            return constants.ExitStatus.FAILURE

        logger.info("Attendance web app available at http://127.0.0.1:8000")
        web_app.run(
            host="127.0.0.1",
            port=8000,
            debug=False,
            threaded=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        logger.info("Attendance web app stopped")
    except Exception as error:
        logger.error(f"Unexpected error occurred: {error}")
        return constants.ExitStatus.FAILURE
    finally:
        camera.close()
        logger.shutdown()

    return constants.ExitStatus.SUCCESS


if __name__ == "__main__":
    sys.exit(main())
