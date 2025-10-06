import bcrypt

plain_password = "admin1234"

hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

print("Mot de passe haché :")
print(hashed_password.decode('utf-8'))