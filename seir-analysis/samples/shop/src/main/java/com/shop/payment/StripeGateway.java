package com.shop.payment;

import com.shop.model.Money;
import org.springframework.stereotype.Component;

@Component
public class StripeGateway implements PaymentGateway {
    @Override
    public PaymentResult charge(String customerRef, Money amount) {
        return new PaymentResult("stripe-" + customerRef, true, "ok");
    }
}
