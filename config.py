import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    COMPANY_NAME = os.getenv("COMPANY_NAME", "CLÍNICA DE FRENOS HÉCTOR LÓPEZ SRL")
    COMPANY_PHONE = os.getenv("COMPANY_PHONE", "809-575-4401")
    COMPANY_RNC = os.getenv("COMPANY_RNC", "1-33-08894-2")
    COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "CALLE 2 NO.5 LOS CIRUELITOS, SANTIAGO R.D")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
