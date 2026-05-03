# main.py
# DisateQ Motor CPE v5.0 -- Entry Point
# BUG-SYS-01: mutex Windows para instancia unica
# -----------------------------------------------------------------------------
"""
Uso:
    python main.py                           # UI PyWebView (modo por defecto)
    python main.py --cli <cliente_alias>     # Modo CLI sin UI
    python main.py --cli <alias> --limit 10  # Limitar comprobantes
    python main.py --cli <alias> --mock      # Modo mock (sin envio real)
"""
import sys
import argparse


def _verificar_instancia_unica() -> object:
    """
    Crea un mutex global de Windows para garantizar instancia unica.
    Si ya hay una instancia corriendo, muestra mensaje y termina.
    Retorna el handle del mutex (debe mantenerse vivo durante toda la sesion).
    """
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, "DisateQMotorCPE_v5_SingleInstance")
        last_error = kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            ctypes.windll.user32.MessageBoxW(
                0,
                "DisateQ Motor CPE ya esta en ejecucion.\n\nRevisa la barra de tareas.",
                "DisateQ Motor CPE",
                0x30  # MB_ICONWARNING
            )
            sys.exit(0)
        return mutex
    except Exception:
        # Si falla el mutex (no Windows), continuar sin restriccion
        return None


def main() -> int:
    # Instancia unica solo en modo UI (no en CLI -- permite multiples procesos batch)
    parser = argparse.ArgumentParser(description='DisateQ Motor CPE v5.0')
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
        # Modo UI -- verificar instancia unica antes de arrancar
        _mutex = _verificar_instancia_unica()

        from src.ui.app import start_app
        return start_app()


if __name__ == '__main__':
    sys.exit(main())
