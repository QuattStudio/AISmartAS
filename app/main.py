from core.logger import logger
from core import constants
from vision.camera import camera
from vision.recogination import referenceEmbedding
from database.mockdb import DataBase


import sys
import json





def main() -> int:
    exitCode = constants.ExitStatus.SUCCESS


    # initialize the logger sub-system
    if not logger.initialize("resources/logs/app.log"):
        print("Logging sub-system failed to initialized!")
        return constants.ExitStatus.FAILURE



    logger.info("WELCOME to AI powered Smart Attendence System")

    database_system = DataBase()

    try:
        if not camera.open():
            exitCode = constants.ExitStatus.FAILURE
            return exitCode
        
        db = database_system.get()
        
        db.commit()
        db.close()

        
        camera.show()


    except Exception:
        logger.error("Unexpected error occurred")
        exitCode = constants.ExitStatus.FAILURE
        raise Exception


    finally:
        try:
            # Initialize camera vision
            if not camera.close():
                exitCode = constants.ExitStatus.FAILURE
 

        finally:
            logger.shutdown()



    return exitCode








if __name__ == "__main__":
    # data = {
    #     "shaury": get_reference_embedding("resources/assets/shaury.jpg"),
    #     "aditya": get_reference_embedding("resources/assets/aditya.jpg"),
    # }
    # with open("resources/data/mock.json", "w", encoding="utf-8") as file:
    #     json.dump(data, file, indent=2)

    
    sys.exit(main())



