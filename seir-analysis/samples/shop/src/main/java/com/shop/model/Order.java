package com.shop.model;

import java.util.List;

public class Order {
    private final String id;
    private final Customer customer;
    private final List<LineItem> items;
    private Status status = Status.NEW;

    public Order(String id, Customer customer, List<LineItem> items) {
        this.id = id;
        this.customer = customer;
        this.items = items;
    }

    public Money total() {
        return items.stream().map(LineItem::price).reduce(Money::plus).orElseThrow();
    }

    public String id() { return id; }
    public Customer customer() { return customer; }
    public List<LineItem> items() { return items; }
    public Status status() { return status; }
    public void markPaid() { status = Status.PAID; }

    public enum Status { NEW, PAID, SHIPPED }

    public record LineItem(String sku, int quantity, Money price) {}
}
