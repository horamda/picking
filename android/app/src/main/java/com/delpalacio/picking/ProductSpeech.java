package com.delpalacio.picking;

final class ProductSpeech {
    static String prompt(String name,int bultos,int units,int pallets,int stage,int index,int total){
        String intro="Producto "+(index+1)+" de "+total+". ";
        if(stage==4 && pallets>0)return intro+"Prepará "+(pallets==1?"un pallet completo":pallets+" pallets completos")+" de "+name+". Cuando termines, decí correcto.";
        java.util.List<String> quantities=new java.util.ArrayList<>();
        if(bultos>0)quantities.add(bultos==1?"un bulto":bultos+" bultos");
        if(units>0)quantities.add(units==1?"una unidad":units+" unidades");
        if(quantities.isEmpty())return intro+name+" no tiene cantidades para preparar. Revisá la planilla con el supervisor.";
        return intro+"Agarrá "+String.join(" y ",quantities)+" de "+name+". Cuando termines, decí correcto. Si falta mercadería, decí faltante.";
    }
}
