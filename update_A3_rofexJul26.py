import os

precio_input = input("Ingresa el precio A3 Soja Julio 2026 (USD/TN): ")

try:
    precio = float(precio_input)
    if precio <= 0:
        raise ValueError(f"el {precio} no puede ser menor a cero")
except ValueError as e:
    print(f"Error: {e}")
    exit(1)

with open("A3_rofexJuly26.txt", "w") as f:
    f.write(str(precio))

print(f"Precio guardado: {precio} USD/TN en A3_rofexJuly26.txt")
