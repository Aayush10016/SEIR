package com.shop.jobs;

import com.shop.payment.LegacyPaymentService;
import org.springframework.scheduling.annotation.Scheduled;

public class ReconciliationJob {
    @Scheduled(cron = "0 0 2 * * *")
    public void run() {
        int settled = LegacyPaymentService.reconcileAll();
        System.out.println("Reconciled " + settled + " legacy payments");
    }
}
