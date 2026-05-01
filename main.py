# main.py
# DisateQ Motor CPE v5.0 — Entry Point
# ─────────────────────────────────────────────────────────────────────────────

"""
Uso:
    python main.py                           # UI PyWebView (modo por defecto)
    python main.py --cli <cliente_alias>     # Modo CLI sin UI
    python main.py --cli <alias> --limit 10  # Limitar comprobantes
    python main.py --cli <alias> --mock      # Modo mock (sin envio real)
"""

import sys
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description='DisateQ™ Motor CPE v5.0')
    parser.add_argument('--cli', metavar='CLIENTE',
                        help='Ejecutar en modo CLI con el alias del cliente')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limite de comprobantes a procesar')
    parser.add_argument('--mock', action='store_true',
                        help='Usar sender mock (sin envio real)')
    args = parser.parse_args()

    if args.cli:
        from src.motor import Motor
        motor = Motor(
            cliente_alias=args.cli,
            modo_sender='mock' if args.mock else None,
        )
        results = motor.procesar(limit=args.limit)
        return 0 if results['errores'] == 0 else 1

    else:
        # Modo UI — PyWebView
        from src.ui.app import start_app
        return start_app()


if __name__ == '__main__':
    sys.exit(main())
