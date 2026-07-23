import argparse
import requests
import urllib3

# Desactivar advertencias de certificados SSL no verificados (para la IP local)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    # 1. Configurar las flags (argumentos de consola)
    parser = argparse.ArgumentParser(
        description="Cliente HTTP para intercambiar datos con otros equipos."
    )

    parser.add_argument(
        "--ip",
        type=str,
        default="172.17.247.252",
        # default="172.17.255.202",
        help="IP o dominio del servidor destino",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="/",
        help="Endpoint a consultar (ejemplo: /api/status o /users)",
    )
    parser.add_argument(
        "--full-data",
        action="store_true",
        help="Flag booleana: si se incluye, pide información detallada",
    )
    parser.add_argument(
        "--send-msg",
        type=str,
        help="Flag con valor: envía un mensaje mediante un POST",
    )

    args = parser.parse_args()

    # 2. Construir la URL completa
    base_url = (
        args.ip if args.ip.startswith("http") else f"https://{args.ip}"
    )
    url = f"{base_url.rstrip('/')}/{args.endpoint.lstrip('/')}"

    print(f"📡 Conectando a: {url} ...")

    # 3. Tomar decisiones con base en las flags
    try:
        # Decisión A: Si pasamos la flag --send-msg, hacemos un POST enviando datos
        if args.send_msg:
            payload = {"mensaje": args.send_msg}
            print(f"📤 Enviando datos (POST): {payload}")
            response = requests.post(url, json=payload, verify=False, timeout=5)

        # Decisión B: Si no enviamos mensaje, hacemos un GET (petición estándar)
        else:
            # La flag --full-data cambia los parámetros que le enviamos a la URL
            params = {"mode": "verbose"} if args.full_data else {"mode": "simple"}
            print(f"📥 Solicitando datos (GET) con parámetros: {params}")
            response = requests.get(url, params=params, verify=False, timeout=5)

        # 4. Mostrar el resultado
        if response.status_code == 200:
            print("✅ ¡Conexión exitosa!")
            try:
                # Intentamos mostrarlo como JSON si el servidor responde con JSON
                print("📄 Respuesta del servidor:", response.json())
            except ValueError:
                # Si responde en texto plano o HTML
                print("📄 Respuesta del servidor:", response.text)
        else:
            print(
                f"⚠️ Servidor respondió con código {response.status_code}: {response.reason}"
            )

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con el servidor: {e}")


if __name__ == "__main__":
    main()