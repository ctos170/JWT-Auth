import re

def validate_password_complexity(v: str,no_white_space_regex) -> str:
        if not re.fullmatch(no_white_space_regex, v):
            raise ValueError("Şifre boşluk içeremez.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Şifre en az bir küçük harf içermelidir.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Şifre en az bir büyük harf içermelidir.")
        if not re.search(r"\d", v):
            raise ValueError("Şifre en az bir rakam içermelidir.")
        if not re.search(r"[@$!%*?&_~]", v):
            raise ValueError("Şifre en az bir özel karakter (@$!%*?&_~) içermelidir.")
        return v

