from . import generic_html


def check(source: dict) -> dict:
    """
    MVP: trata el sumario del BOCM como HTML genérico (lista de disposiciones del día).
    TODO (siguiente iteración): parsear el PDF de "Vivienda" / "Urbanismo" directamente
    y extraer título + nº de boletín + enlace de cada disposición, en vez de hashear
    la página entera (ahora mismo cualquier cambio de sumario, sea o no de vivienda,
    dispara una alerta -> hay que revisar el resumen a mano antes de reenviar a Sergio).
    """
    return generic_html.check(source)
