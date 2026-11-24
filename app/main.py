from core.logger import logger
from core import constants
from vision.camera import camera

import sys





def main() -> int:
    exitCode = constants.exit_status.SUCCESS


    # initialize the logger sub-system
    if not logger.initialize("resources/logs/app.log"):
        print("Logging sub-system failed to initialized!")
        return constants.exit_status.FAILURE



    logger.info("WELCOME to AI powered Smart Attendence System")


    try:
        if not camera.open():
            exitCode = constants.exit_status.FAILURE
            return exitCode
        

        camera.show()


    except Exception:
        logger.error("Unexpected error occurred")
        exitCode = constants.exit_status.FAILURE


    finally:
        try:
            # Initialize camera vision
            if not camera.close():
                exitCode = constants.exit_status.FAILURE


        finally:
            logger.shutdown()



    return exitCode











if __name__ == "__main__":
    sys.exit(main())



