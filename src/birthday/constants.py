

#Environment related constants
ENV_PRODUCTION = 'PRODUCTION'
#Staging is used for testing by replicating the same production remote env
ENV_STAGING = 'STAGING'
#Development local env
ENV_DEVELOPMENT = 'DEV'
#Automated tests local env
ENV_TESTING = 'TEST'

ENVIRONMENT_CHOICES = [
    ENV_PRODUCTION,
    ENV_STAGING,
    ENV_DEVELOPMENT,
    ENV_TESTING,
]

EMAIL_REGEXP = "^[a-zA-Z0-9'._-]+@[a-zA-Z0-9._-]+.[a-zA-Z]{2,6}$"

MALE = 'M'
FEMALE = 'F'
OTHER = 'O'

GENDERS = [
    MALE,
    FEMALE,
    OTHER
]

OAUTH2_SCOPES = 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/admin.directory.user.readonly https://www.googleapis.com/auth/plus.profiles.read https://www.googleapis.com/auth/plus.me https://www.googleapis.com/auth/plus.login https://www.googleapis.com/auth/calendar https://www.google.com/m8/feeds'

BIRTHDAY_CSV_COLUMNS = ["email", "birthday"]

MENU_ITEMS = [
    ('admin_index', 'Home'),
    ('upload_csv', 'Upload'),
    ('settings', 'Settings'),
]