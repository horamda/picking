package com.delpalacio.picking;

import java.text.Normalizer;
import java.util.*;
import java.util.regex.*;

/** Exact quantity phrases only. Never confirms or saves a shortage. */
final class VoiceQuantities {
    private static final Map<String,Integer> NUMBERS = new LinkedHashMap<>();
    static {
        String[] small={"cero","uno","dos","tres","cuatro","cinco","seis","siete","ocho","nueve","diez","once","doce","trece","catorce","quince","dieciseis","diecisiete","dieciocho","diecinueve","veinte","veintiuno","veintidos","veintitres","veinticuatro","veinticinco","veintiseis","veintisiete","veintiocho","veintinueve"};
        for(int i=0;i<small.length;i++)NUMBERS.put(small[i],i);
        String[] tens={"treinta","cuarenta","cincuenta","sesenta","setenta","ochenta","noventa"};
        for(int i=0;i<tens.length;i++)for(int j=0;j<10;j++)NUMBERS.put(tens[i]+(j==0?"":" y "+small[j]),30+i*10+j);
        Map<String,Integer> underHundred=new LinkedHashMap<>(NUMBERS);
        String[] hundreds={"ciento","doscientos","trescientos","cuatrocientos","quinientos","seiscientos","setecientos","ochocientos","novecientos"};
        for(int i=0;i<hundreds.length;i++)for(Map.Entry<String,Integer> n:underHundred.entrySet()) {
            if(n.getValue()==0) NUMBERS.put(i==0?"cien":hundreds[i],(i+1)*100);
            else NUMBERS.put(hundreds[i]+" "+n.getKey(),(i+1)*100+n.getValue());
        }
        Map<String,Integer> aliases=new LinkedHashMap<>();
        for(Map.Entry<String,Integer> n:NUMBERS.entrySet()) {
            if(n.getKey().endsWith("uno")) {
                aliases.put(n.getKey().substring(0,n.getKey().length()-3)+"un",n.getValue());
                aliases.put(n.getKey().substring(0,n.getKey().length()-3)+"una",n.getValue());
            }
        }
        NUMBERS.putAll(aliases);
    }
    static String normalize(String value) {
        return Normalizer.normalize(value.toLowerCase(Locale.ROOT),Normalizer.Form.NFD)
            .replaceAll("\\p{M}","").trim().replaceAll("\\s+"," ");
    }
    static Integer[] parse(String input) {
        String text=normalize(input);
        Matcher matcher=Pattern.compile("(.+?) (bultos?|unidad(?:es)?)(?: |$)").matcher(text);
        Integer[] values=new Integer[2]; int end=0;
        while(matcher.find()) {
            if(matcher.start()!=end)return null;
            String number=matcher.group(1);
            Integer value=NUMBERS.get(number);
            if(number.matches("[0-9]{1,3}"))value=Integer.valueOf(number);
            int slot=matcher.group(2).startsWith("bulto")?0:1;
            if(value==null || values[slot]!=null)return null;
            values[slot]=value; end=matcher.end();
        }
        return end==text.length() && end>0 ? values : null;
    }
    static Set<String> vocabulary() {
        Set<String> words=new TreeSet<>();
        for(String number:NUMBERS.keySet())words.addAll(Arrays.asList(number.split(" ")));
        words.addAll(Arrays.asList("bulto","bultos","unidad","unidades"));
        return words;
    }
}
