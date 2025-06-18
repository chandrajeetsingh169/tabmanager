package com.company;
import java.util.Scanner;

 public class hel {


    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        // Input two numbers
        System.out.print("Enter first number: ");
        int num1 = scanner.nextInt();

        System.out.print("Enter second number: ");
        int num2 = scanner.nextInt();

        // Calculate sum
        int sum = num1 + num2;

        // Display result
    System.out.println("Sum: " + sum);
    scanner.close();
    
}
}



