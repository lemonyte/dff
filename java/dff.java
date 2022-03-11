package java;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
//import java.nio.file.Files;
//import java.nio.file.Path;
//import java.nio.file.Paths;
//import java.util.*;
//import java.util.stream.*;
//import java.util.List;
//import java.util.ArrayList;

public class dff
{
    public static void main(String[] args) throws NoSuchAlgorithmException, IOException
    {
        System.out.println("Calculating full hashes...");
        System.out.println(CalculateFullHash(""));
    }

    private static String CalculateFullHash(String filePath) throws NoSuchAlgorithmException, IOException
    {
        //Get file input stream for reading the file content
        File file = new File(filePath);
        FileInputStream fis = new FileInputStream(file);
        
        //Create byte array to read data in chunks
        byte[] byteArray = new byte[1024];
        int bytesCount = 0;
        MessageDigest messageDigest = MessageDigest.getInstance("MD5");

        //Read file data and update in message digest
        while ((bytesCount = fis.read(byteArray)) != -1)
        {
            messageDigest.update(byteArray, 0, bytesCount);
        };

        //Close the stream
        fis.close();

        //Get the hash's bytes
        byte[] bytes = messageDigest.digest();

        //This bytes[] has bytes in decimal format
        //Convert it to hexadecimal format
        StringBuilder sb = new StringBuilder();
        
        for (int i=0; i< bytes.length ;i++)
        {
            sb.append(Integer.toString((bytes[i] & 0xff) + 0x100, 16).substring(1));
        }

        //Return the complete hash
        return sb.toString();
    }
}