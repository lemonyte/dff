package Java;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class dff {
    public static void main(String[] args) throws IOException {
        System.out.println("Hello world!");

        String fileName = "duplicate-file-finder/files/test.txt";
        Path filePath = Paths.get(fileName);
        long fileSize = Files.size(filePath);

        System.out.println(fileSize);
    }
}