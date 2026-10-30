package com.delpalacio.picking;
final class ProductCode {
    static String parse(String speech){
        if(speech==null)return "";
        String text=speech.trim().toLowerCase(java.util.Locale.ROOT);
        String[] names={"cero","uno","dos","tres","cuatro","cinco","seis","siete","ocho","nueve"};
        StringBuilder code=new StringBuilder();
        for(String token:text.split("\\s+")){
            if(token.matches("[0-9]+")){code.append(token);continue;}
            int found=-1;for(int n=0;n<names.length;n++)if(names[n].equals(token))found=n;
            if(found<0)return "";code.append(found);
        }
        return code.toString();
    }
}
