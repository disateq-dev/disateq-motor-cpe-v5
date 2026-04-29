"""
main.py
=======
Motor CPE DisateQ™ v5.0 — Entry Point

Uso:
    python main.py                          # UI Eel (modo por defecto)
    python main.py --cli <cliente_alias>    # Modo CLI sin UI
    python main.py --cli <alias> --limit 10 # Limitar comprobantes
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Motor CPE DisateQ™ v5.0'
    )
    parser.add_argument('--cli', metavar='CLIENTE',
                        help='Ejecutar en modo CLI con el alias del cliente')
    parser.add_argument('--limit', type=int, default=None,
                        help='Límite de comprobantes a procesar')
    parser.add_argument('--mock', action='store_true',
                        help='Usar sender mock (sin envío real)')

    args = parser.parse_args()

    if args.cli:
        # Modo CLI
        from src.motor import Motor
        motor = Motor(
            cliente_alias=args.cli,
            modo_sender='mock' if args.mock else None
        )
        results = motor.procesar(limit=args.limit)
        return 0 if results['errores'] == 0 else 1
    else:
        # Modo UI (Eel)
        from src.ui.backend.app import start_app
        start_app()
        return 0


if __name__ == '__main__':
    sys.exit(main())
