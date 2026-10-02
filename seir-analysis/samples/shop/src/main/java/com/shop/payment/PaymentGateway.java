package com.shop.payment;

import com.shop.model.Money;

public interface PaymentGateway {
    PaymentResult charge(String customerRef, Money amount);
}
