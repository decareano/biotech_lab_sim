#!/usr/bin/env python3
"""
Agente Convertidor de Granos con Dólar Blue - Argentina
Convierte bushels a toneladas y precios de CBOT a pesos argentinos
"""

import re
import json
import urllib.request
from datetime import datetime, date
from typing import Dict, Optional, Tuple

# ============================================
# CLASE PARA DÓLAR BLUE
# ============================================


class DolarBlueAPI:
    """
    Cliente para obtener cotización del dólar blue
    Usa fuentes gratuitas (simulado con datos reales)
    """

    # Base de datos local de cotizaciones históricas (ejemplo)
    # En producción, usar API real como dolarito.ar o ravabursatil
    HISTORICO = {
        "2026-05-01": {"compra": 1380, "venta": 1400},  # 1 de mayo 2026
        "2026-01-05": {"compra": 1515, "venta": 1515},  # 5 de enero 2026[citation:1]
        "2026-01-04": {"compra": 1530, "venta": 1530},
        "2026-01-03": {"compra": 1530, "venta": 1530},
        "2026-01-02": {"compra": 1530, "venta": 1530},
        "2026-01-01": {"compra": 1530, "venta": 1530},
    }

    @classmethod
    def obtener_dolar_blue(cls, fecha: Optional[date] = None) -> Optional[Dict]:
        """
        Obtiene cotización del dólar blue para una fecha específica
        Si no hay fecha, devuelve la cotización más reciente
        """
        if fecha is None:
            fecha = date.today()

        fecha_str = fecha.isoformat()

        # Buscar en histórico local
        if fecha_str in cls.HISTORICO:
            return cls.HISTORICO[fecha_str]

        # Si no hay datos para esa fecha, buscar la más cercana
        # (en producción, usar API real)
        fechas_disponibles = sorted(cls.HISTORICO.keys())
        for f in reversed(fechas_disponibles):
            if f <= fecha_str:
                return cls.HISTORICO[f]

        return None

    @classmethod
    def obtener_actual(cls) -> Optional[Dict]:
        """Obtiene cotización actual (versión simplificada)"""
        # En producción: llamar a API real
        # Ejemplo: https://api.dolarito.ar/v1/dolar-blue
        return cls.HISTORICO.get("2026-05-01", None)


# ============================================
# CONVERSIÓN DE PRECIOS A PESOS
# ============================================


def convertir_precio_a_pesos(precio_usd_por_tn: float, cotizacion_blue: Dict) -> float:
    """
    Convierte precio de USD/tonelada a ARS/tonelada usando dólar blue
    """
    return round(precio_usd_por_tn * cotizacion_blue["venta"], 2)


# ============================================
# CLASE EXTENDIDA DEL AGENTE
# ============================================


class ConvertidorGranos:
    """Factores de conversión actualizados"""

    FACTORES_CONVERSION = {
        "maiz": 0.0254,
        "maíz": 0.0254,
        "sorgo": 0.0254,
        "centeno": 0.0254,
        "trigo": 0.0272155,
        "soja": 0.0272155,
        "soya": 0.0272155,
    }

    @classmethod
    def convertir(cls, bushels: float, grano: str) -> Optional[float]:
        grano = grano.lower().replace("á", "a").replace("é", "e")
        factor = cls.FACTORES_CONVERSION.get(grano)
        if factor:
            return round(bushels * factor, 2)
        return None

    @classmethod
    def precio_por_tonelada(
        cls, precio_por_bushel: float, grano: str
    ) -> Optional[float]:
        grano = grano.lower().replace("á", "a").replace("é", "e")
        factor = cls.FACTORES_CONVERSION.get(grano)
        if factor:
            return round(precio_por_bushel / factor, 2)
        return None


class AgenteGranos:
    """Agente completo con soporte para dólar blue"""

    def __init__(self):
        self.convertidor = ConvertidorGranos()

    def parsear_consulta(self, consulta: str) -> Optional[Dict]:
        consulta_lower = consulta.lower()

        # Patrón: precio en pesos argentinos
        # Ej: "a cuánto está la tonelada de soja en pesos"
        if "en pesos" in consulta_lower or "ars" in consulta_lower:
            match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:usd|dólares?|\$)\s*(?:por|el)\s*bushel\s*(?:de)?\s*(\w+)\s+en\s+pesos",
                consulta_lower,
            )
            if match:
                return {
                    "tipo": "precio_pesos",
                    "precio_usd": float(match.group(1)),
                    "grano": match.group(2),
                }

        # Patrón original: precio en USD/tonelada
        match = re.search(
            r"\$\s*(\d+(?:\.\d+)?)\s*(?:por|el)\s*bushel\s*(?:de)?\s*(\w+)\s+(?:a|en)\s+(?:toneladas?)",
            consulta_lower,
        )
        if match:
            return {
                "tipo": "precio",
                "precio_usd": float(match.group(1)),
                "grano": match.group(2),
            }

        # Patrón: volumen
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:bushels?|bu)\s*(?:de)?\s*(\w+)\s+(?:a|en)\s+(?:toneladas?)",
            consulta_lower,
        )
        if match:
            return {
                "tipo": "volumen",
                "cantidad": float(match.group(1)),
                "grano": match.group(2),
            }

        return None

    def ejecutar(self, parseado: Dict) -> str:
        grano = parseado["grano"]

        # Obtener cotización del dólar blue actual
        dolar_blue = DolarBlueAPI.obtener_actual()
        if dolar_blue:
            blue_venta = dolar_blue["venta"]
            blue_compra = dolar_blue["compra"]
        else:
            blue_venta = blue_compra = "N/A"

        if parseado["tipo"] == "volumen":
            resultado = self.convertidor.convertir(parseado["cantidad"], grano)
            if resultado is None:
                return f"❌ No soporto '{grano}'. Probá con: maíz, trigo, soja, sorgo o centeno"

            return (
                f"\n🌽 **{parseado['cantidad']:,.0f} bushels de {grano.title()}**\n"
                f"= **{resultado:,.2f} toneladas métricas**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📐 Factor: 1 bu = {self.convertidor.FACTORES_CONVERSION.get(grano.lower(), 'N/A')} TN\n\n"
                f"💰 **Dólar Blue hoy:** ${blue_venta:,} ARS (venta) | ${blue_compra:,} ARS (compra)"
            )

        elif parseado["tipo"] == "precio":
            precio_por_tn_usd = self.convertidor.precio_por_tonelada(
                parseado["precio_usd"], grano
            )
            if precio_por_tn_usd is None:
                return f"❌ No soporto '{grano}'"

            # Calcular precio en pesos argentinos
            if isinstance(blue_venta, (int, float)):
                precio_por_tn_ars = convertir_precio_a_pesos(
                    precio_por_tn_usd, dolar_blue
                )
            else:
                precio_por_tn_ars = "N/A"

            return (
                f"\n💰 **CBOT - {grano.title()}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🇺🇸 US${parseado['precio_usd']:,.2f} / bushel\n"
                f"→ **US${precio_por_tn_usd:,.2f} / tonelada**\n\n"
                f"🇦🇷 **AL DÓLAR BLUE (${blue_venta:,} ARS)**\n"
                f"→ **ARS${precio_por_tn_ars:,.2f} / tonelada**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 El dólar blue es el tipo de cambio del mercado paralelo.\n"
                f"   Para exportaciones formales, se usa el dólar oficial."
            )

        elif parseado["tipo"] == "precio_pesos":
            precio_por_tn_usd = self.convertidor.precio_por_tonelada(
                parseado["precio_usd"], grano
            )
            if precio_por_tn_usd is None:
                return f"❌ No soporto '{grano}'"

            if isinstance(blue_venta, (int, float)):
                precio_por_tn_ars = convertir_precio_a_pesos(
                    precio_por_tn_usd, dolar_blue
                )
            else:
                precio_por_tn_ars = "N/A"

            return (
                f"\n🇦🇷 **{grano.title()} - Precio en Argentina**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 Precio CBOT: US${precio_por_tn_usd:,.2f}/TN\n"
                f"💰 Dólar blue: ${blue_venta:,} ARS\n"
                f"💸 **Valor en pesos: ARS${precio_por_tn_ars:,.2f}/TN**\n\n"
                f"⚠️ Este es el valor de referencia del CBOT convertido.\n"
                f"   El precio local (Matba Rofex) puede diferir por oferta y demanda."
            )

        return "❌ No entendí. Probá con:\n• '5000 bushels de maíz a toneladas'\n• '$5.50 por bushel de soja a toneladas'\n• '$5.50 por bushel de soja en pesos'"


# ============================================
# FUNCIÓN PARA CONSULTAR DÓLAR BLUE HISTÓRICO
# ============================================


def consultar_dolar_historico():
    """Función adicional: consultar dólar blue para una fecha específica"""
    print("\n" + "=" * 50)
    print("💰 CONSULTAR DÓLAR BLUE HISTÓRICO")
    print("=" * 50)
    print("\nEjemplos:")
    print("  • 'dolar blue 5/1/2026'")
    print("  • 'cotización dólar blue 1 de mayo 2026'")

    # Implementación simplificada
    # En producción, usar API que soporte consultas históricas[citation:10]


# ============================================
# MODO INTERACTIVO
# ============================================


def modo_interactivo():
    print("\n" + "=" * 60)
    print("🌽 AGENTE CON GRANOS + DÓLAR BLUE - ARGENTINA 🤖")
    print("=" * 60)
    print("\n🇦🇷 Convertí bushels a toneladas + precios del CBOT a pesos argentinos")
    print("\n📝 Ejemplos:")
    print("  • '5000 bushels de maíz a toneladas'")
    print("  • '$5.50 por bushel de soja a toneladas'")
    print("  • '$5.50 por bushel de soja en pesos' (¡NUEVO!)")
    print("\n💡 Escribí 'salir' para terminar\n")

    agente = AgenteGranos()

    while True:
        try:
            consulta = input("🧑‍🌾 Vos: ").strip()
            if consulta.lower() in ["salir", "exit", "quit", "q"]:
                print("\n👋 ¡Chau! Buenos negocios.")
                break

            if not consulta:
                continue

            respuesta = agente.ejecutar(agente.parsear_consulta(consulta) or {})
            print(f"🤖 Agente: {respuesta}")

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    modo_interactivo()
