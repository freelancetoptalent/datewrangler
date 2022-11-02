##
## TESTING DATABASE
##

# Local settings for sensitive information
EMAIL_SUBJECT_PREFIX = '[PSD Sandbox] '

EMAIL_HOST_USER = 'sandboxPSD@gmail.com'
EMAIL_HOST_PASSWORD = 'happy-dancing-10?'

ADMINS = (
    ('Luke Miratrix', 'info@polyspeeddating.com'),
)
ADMIN_FOR = ('register','psd.register',)

MANAGERS = (
    ('Luke Miratrix', 'info@polyspeeddating.com'),
)


DB_NAME = 'sandbox_database'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'u^(sfsfdfsdfsfsnxshnltsdfydnty][p][fgbmselri454sd54sdfgsdgfv4509slaes32xcmnxcmvsdfsdfswlgijgjgksjhtgsrtghs'


# For Stripe payment
STRIPE_KEY = 'pk_test_W0KQm1AEqJZhtUc7pvgNG64L007wdGWxH9'
STRIPE_PRODUCT = 'sku_FWPrzPhUJz6pU6'


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


# override templates
INSTALLED_APPS[INSTALLED_APPS.index('sites.base')] = 'sites.sandbox'

print(INSTALLED_APPS)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, DB_NAME),
    }
}


print "Database '%s'" % ( DATABASES['default']['NAME'], )

print "Local settings loaded\n"
