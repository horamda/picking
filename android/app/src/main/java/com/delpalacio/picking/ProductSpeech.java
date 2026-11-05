package com.delpalacio.picking;

final class ProductSpeech {
    static String separation(String reparto, boolean compact, boolean separated) {
        if (!separated) return "";
        return "Reparto " + reparto + ". " + (compact ? "Supermercado. Armado compacto para descarga con autoelevador. " : "")
            + "Armá separado. No mezcles con otros repartos ni con otro camión. ";
    }
    static String destination(String id, int bultos, int units, boolean shared) {
        java.util.List<String> quantities = new java.util.ArrayList<>();
        if (bultos > 0) quantities.add(bultos == 1 ? "un bulto" : bultos + " bultos");
        if (units > 0) quantities.add(units == 1 ? "una unidad" : units + " unidades");
        if (quantities.isEmpty()) return "";
        return "Pallet " + id + ": colocá " + String.join(" y ", quantities) + ". "
            + (shared ? "Compartido con otras canchas. " : "");
    }
    static String prompt(String name,int bultos,int units,int pallets,int stage,int index,int total){
        return prompt(name,bultos,units,pallets,stage,index,total,"");
    }
    static String prompt(String name,int bultos,int units,int pallets,int stage,int index,int total,String freshness){
        String intro="Producto "+(index+1)+" de "+total+". ";
        String freshnessText=freshness==null||freshness.isEmpty()?"":" Frescura "+freshness+".";
        if(stage==4 && pallets>0)return intro+"Prepará "+(pallets==1?"un pallet completo":pallets+" pallets completos")+" de "+name+"."+freshnessText;
        java.util.List<String> quantities=new java.util.ArrayList<>();
        if(bultos>0)quantities.add(bultos==1?"un bulto":bultos+" bultos");
        if(units>0)quantities.add(units==1?"una unidad":units+" unidades");
        if(quantities.isEmpty())return intro+name+" no tiene cantidades para preparar. Revisá la planilla con el supervisor.";
        if(stage==1 || stage==2)return intro+"Verificá "+String.join(" y ",quantities)+" de "+name+"."+freshnessText;
        return intro+"Agarrá "+String.join(" y ",quantities)+" de "+name+"."+freshnessText;
    }
}
