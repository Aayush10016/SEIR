package com.shop.model;

import java.math.BigDecimal;

public record Money(BigDecimal amount, String currency) {
    public Money plus(Money other) {
        return new Money(amount.add(other.amount()), currency);
    }
}
