from core.logger import logger






if __name__ == "__main__":
    # initialize the logger sub-system
    logger.initialize("resources/logs/app.log")

    logger.info("WELCOME to AI powered Smart Attendence System")

    # shutdown the logger sub-system
    logger.shutdown()


