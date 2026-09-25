from rest_framework.throttling import SimpleRateThrottle


class PlatonusVerifyThrottle(SimpleRateThrottle):
    scope = "platonus_verify"
    rate = "5/min"

    def get_cache_key(self, request, view):
        # Для текущего локального запуска без reverse proxy.
        ip_address = request.META.get("REMOTE_ADDR", "unknown")

        return self.cache_format % {
            "scope": self.scope,
            "ident": ip_address,
        }