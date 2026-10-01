package com.shop.payment;

import com.shop.model.Money;
import java.util.ArrayList;
import java.util.List;

/** Old in-house processor. Scheduled for removal. */
@Deprecated
public class LegacyPaymentService implements PaymentGateway {
    private static final List<String> LEDGER = new ArrayList<>();

    @Override
    public PaymentResult charge(String customerRef, Money amount) {
        LEDGER.add(customerRef + ":" + amount.amount());
        return new PaymentResult("legacy-" + LEDGER.size(), true, "ok");
    }

    public static int reconcileAll() {
        int count = LEDGER.size();
        LEDGER.clear();
        return count;
    }
}
