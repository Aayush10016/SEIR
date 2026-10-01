package com.shop.jobs;

import com.shop.payment.PaymentGateway;

/** Not referenced anywhere - candidate dead code. */
public class AuditJob {
    private final PaymentGateway gateway;

    public AuditJob(PaymentGateway gateway) {
        this.gateway = gateway;
    }
}
