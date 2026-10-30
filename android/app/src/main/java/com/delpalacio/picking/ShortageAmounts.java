package com.delpalacio.picking;

final class ShortageAmounts {
    static String error(String b, String u, int expectedB, int expectedU) {
        try {
            int foundB=Integer.parseInt(b), foundU=Integer.parseInt(u);
            if(foundB<0 || foundU<0 || foundB>expectedB || foundU>expectedU)
                return "La cantidad encontrada debe estar entre cero y lo pedido en la planilla.";
            if(foundB==expectedB && foundU==expectedU)
                return "Encontraste toda la cantidad. Cancelá y usá Correcto; no hay faltante.";
            return "";
        } catch(NumberFormatException e) { return "Completá ambos campos con números enteros. Si no encontraste nada, ingresá cero."; }
    }
    static String summary(String b, String u, int expectedB, int expectedU) {
        String error=error(b,u,expectedB,expectedU);
        if(!error.isEmpty())return error;
        return "Faltan: "+(expectedB-Integer.parseInt(b))+" bultos + "+(expectedU-Integer.parseInt(u))+" unidades.";
    }
}
