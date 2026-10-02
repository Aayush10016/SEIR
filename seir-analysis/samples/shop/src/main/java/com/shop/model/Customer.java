package com.shop.model;

public class Customer {
    private final String email;

    public Customer(String email) {
        this.email = email;
    }

    public String email() {
        return email;
    }
}
