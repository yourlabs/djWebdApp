from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from pytezos.crypto.key import Key

UserModel = get_user_model()


class ModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):
        if not (
            "public_key" in request._post
            and "public_key_hash" in request._post
            and "message" in request._post
            and "signed_message" in request._post
        ):
            return super().authenticate(request, username, password)

        public_key_alphanum = request._post["public_key"]
        public_key_hash = request._post["public_key_hash"]
        message = request._post["message"]
        signed_message = request._post["signed_message"]

        public_key = Key.from_encoded_key(public_key_alphanum)
        try:
            public_key.verify(signed_message, message)

            user, created = UserModel._default_manager.get_or_create(
                public_key_hash=public_key_hash,
            )
            if created:
                user.public_key = public_key_alphanum
                user.password = UserModel.objects.make_random_password()
                user.username = public_key_hash
                user.save()

            if self.user_can_authenticate(user):
                breakpoint()
                return user
        except ValueError:
            return


"""
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

csrftoken = getCookie('csrftoken');


body = new FormData()
body.append("csrfmiddlewaretoken", csrftoken)
body.append("username", "username")
body.append("password", "password")
body.append("public_key", "edpkuhJRth9s12SApCJBwgdCpcHbjxqth6HXCZBwAnheSoysqKT23R")
body.append("public_key_hash", "tz1Yigc57GHQixFwDEVzj5N1znSCU3aq15td")
body.append("message", "message")
body.append("signed_message", "edsigtjf22PVvcVUUywvr56s8VHxxV8gmWv5QgFaK3LoUYhJw4xBobUKggtgfNatP7XhxbEoNSKP6qWqSXWvz12KkuA7RRCZdTi")
body.append("next", "/admin/")
rawResponse = await fetch('/admin/login/?next=/admin/', {
    method: 'POST',
    body
  })
"""
