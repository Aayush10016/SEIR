package com.shop.payment;

import org.junit.jupiter.api.Test;

class PaymentServiceTest {
    @Test
    void refundIsUnsupported() {
        PaymentService service = new PaymentService(new StripeGateway(), new LegacyPaymentService());
        assert !service.refund("tx").success();
    }
}
