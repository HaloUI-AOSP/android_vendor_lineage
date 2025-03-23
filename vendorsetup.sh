# Shebang is intentionally missing - do not run as a script

# Override host metadata to make builds more reproducible and avoid leaking info
[ -z "${BUILD_USERNAME}" ] && export BUILD_USERNAME=android-build
[ -z "${BUILD_HOSTNAME}" ] && export BUILD_HOSTNAME=r-0123456789abcdef-acab
