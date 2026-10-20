from rest_framework.throttling import SimpleRateThrottle


class PlatonusVerifyThrottle(SimpleRateThrottle):
    scope = "platonus_verify"
    rate = "5/min"

    
    def get_cache_key(self, request, view):
        ip_address = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ip_address,
        }
    
class RegistrationCompleteThrottle(PlatonusVerifyThrottle):
    scope = "registration_complete"
    rate = "10/min"