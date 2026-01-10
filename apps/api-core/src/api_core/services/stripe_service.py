"""Stripe payment provider integration service."""

import logging
from typing import Any, Dict, Optional

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.config import get_settings
from api_core.database.models import Plan, User
from api_core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class StripeService:
    """Service for Stripe payment operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize Stripe service.

        Args:
            session: Database session
        """
        self.session = session
        settings = get_settings()

        if not settings.stripe.is_configured:
            logger.warning(
                "Stripe is not configured. Payment operations will fail. "
                "Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY environment variables."
            )

        # Configure Stripe
        stripe.api_key = settings.stripe.secret_key
        stripe.api_version = settings.stripe.api_version

    async def get_or_create_customer(self, user: User) -> str:
        """
        Get or create Stripe customer for user.

        Args:
            user: User database model

        Returns:
            Stripe customer ID

        Raises:
            ValidationError: If Stripe is not configured
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot create customer.")

        # Check if user already has a Stripe customer ID
        # Note: This assumes stripe_customer_id field exists on User model
        # We'll need to add this field in a migration
        if hasattr(user, "stripe_customer_id") and user.stripe_customer_id:
            return user.stripe_customer_id

        # Create customer in Stripe
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={
                    "user_id": user.id,
                    "firm_id": user.firm_id or "",
                },
            )

            # Update user record with Stripe customer ID
            if hasattr(user, "stripe_customer_id"):
                user.stripe_customer_id = customer.id
                await self.session.commit()
                logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            else:
                logger.warning(
                    f"User model does not have stripe_customer_id field. "
                    f"Customer {customer.id} created but not saved to database."
                )

            return customer.id

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer for user {user.id}: {e}")
            raise ValidationError(f"Failed to create Stripe customer: {str(e)}")

    async def create_checkout_session(
        self,
        user: User,
        plan: Plan,
        success_url: str,
        cancel_url: str,
        trial_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create Stripe Checkout session for subscription.

        Args:
            user: User database model
            plan: Plan database model
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancellation
            trial_days: Optional number of trial days

        Returns:
            Dictionary with session_id and url

        Raises:
            ValidationError: If Stripe is not configured or plan is invalid
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot create checkout session.")

        if not plan.price_monthly:
            raise ValidationError(f"Plan {plan.id} does not have a monthly price.")

        try:
            customer_id = await self.get_or_create_customer(user)

            # Convert price to cents
            price_amount = int(float(plan.price_monthly) * 100)

            # Create or retrieve Stripe Price
            # In production, you might want to cache/store Stripe Price IDs
            # Note: product_data doesn't support description in current API version
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency=settings.billing.currency,
                recurring={
                    "interval": "month",
                    "interval_count": 1,
                },
                product_data={
                    "name": plan.display_name,
                },
                metadata={
                    "plan_id": plan.id,
                    "plan_description": plan.description or "",  # Store description in metadata instead
                },
            )

            # Create checkout session
            session_params: Dict[str, Any] = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{"price": price.id, "quantity": 1}],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "user_id": user.id,
                    "plan_id": plan.id,
                },
            }

            if trial_days and trial_days > 0:
                session_params["subscription_data"] = {
                    "trial_period_days": trial_days,
                }

            session = stripe.checkout.Session.create(**session_params)

            logger.info(
                f"Created checkout session {session.id} for user {user.id}, plan {plan.id}"
            )
            return {
                "session_id": session.id,
                "url": session.url,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise ValidationError(f"Failed to create checkout session: {str(e)}")

    async def create_subscription(
        self,
        user: User,
        plan: Plan,
        payment_method_id: str,
        trial_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create subscription directly (for API-based flow).

        Args:
            user: User database model
            plan: Plan database model
            payment_method_id: Stripe payment method ID
            trial_days: Optional number of trial days

        Returns:
            Stripe subscription object as dictionary

        Raises:
            ValidationError: If Stripe is not configured or plan is invalid
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot create subscription.")

        if not plan.price_monthly:
            raise ValidationError(f"Plan {plan.id} does not have a monthly price.")

        try:
            customer_id = await self.get_or_create_customer(user)

            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )

            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id,
                },
            )

            # Create price
            price_amount = int(float(plan.price_monthly) * 100)
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency=settings.billing.currency,
                recurring={"interval": "month"},
                product_data={
                    "name": plan.display_name,
                    "description": plan.description or "",
                },
                metadata={"plan_id": plan.id},
            )

            # Create subscription
            subscription_params: Dict[str, Any] = {
                "customer": customer_id,
                "items": [{"price": price.id}],
                "metadata": {
                    "user_id": user.id,
                    "plan_id": plan.id,
                },
            }

            if trial_days and trial_days > 0:
                subscription_params["trial_period_days"] = trial_days

            subscription = stripe.Subscription.create(**subscription_params)

            logger.info(
                f"Created Stripe subscription {subscription.id} for user {user.id}, plan {plan.id}"
            )
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            raise ValidationError(f"Failed to create subscription: {str(e)}")

    async def cancel_subscription(
        self,
        stripe_subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """
        Cancel Stripe subscription.

        Args:
            stripe_subscription_id: Stripe subscription ID
            cancel_at_period_end: Whether to cancel at period end or immediately

        Returns:
            Updated Stripe subscription object as dictionary

        Raises:
            ValidationError: If subscription not found or cancellation fails
        """
        if not stripe_subscription_id:
            raise ValidationError("Stripe subscription ID is required")

        try:
            if cancel_at_period_end:
                # Cancel at period end
                subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                # Cancel immediately
                subscription = stripe.Subscription.delete(stripe_subscription_id)

            logger.info(
                f"Canceled Stripe subscription {stripe_subscription_id} "
                f"(at_period_end={cancel_at_period_end})"
            )
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription {stripe_subscription_id}: {e}")
            if "No such subscription" in str(e):
                raise NotFoundError(f"Stripe subscription {stripe_subscription_id} not found")
            raise ValidationError(f"Failed to cancel subscription: {str(e)}")

    async def get_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve a Stripe Checkout session.

        Args:
            session_id: Stripe Checkout session ID

        Returns:
            Checkout session object as dictionary

        Raises:
            ValidationError: If session not found or retrieval fails
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot retrieve checkout session.")

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving checkout session {session_id}: {e}")
            raise ValidationError(f"Failed to retrieve checkout session: {str(e)}")

    async def update_subscription_plan(
        self,
        stripe_subscription_id: str,
        new_plan: Plan,
        prorate: bool = True,
    ) -> Dict[str, Any]:
        """
        Update subscription to new plan.

        Args:
            stripe_subscription_id: Stripe subscription ID
            new_plan: New plan database model
            prorate: Whether to prorate the billing

        Returns:
            Updated Stripe subscription object as dictionary

        Raises:
            ValidationError: If subscription not found or update fails
            NotFoundError: If plan is invalid
        """
        if not stripe_subscription_id:
            raise ValidationError("Stripe subscription ID is required")

        if not new_plan.price_monthly:
            raise NotFoundError(f"Plan {new_plan.id} does not have a monthly price.")

        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot update subscription.")

        try:
            # Get current subscription
            current_subscription = stripe.Subscription.retrieve(stripe_subscription_id)

            # Create new price
            price_amount = int(float(new_plan.price_monthly) * 100)
            price = stripe.Price.create(
                unit_amount=price_amount,
                currency=settings.billing.currency,
                recurring={"interval": "month"},
                product_data={"name": new_plan.display_name},
                metadata={"plan_id": new_plan.id},
            )

            # Update subscription
            updated_subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                items=[
                    {
                        "id": current_subscription["items"]["data"][0].id,
                        "price": price.id,
                    }
                ],
                proration_behavior="create_prorations" if prorate else "none",
                metadata={
                    "user_id": current_subscription.metadata.get("user_id", ""),
                    "plan_id": new_plan.id,
                },
            )

            logger.info(
                f"Updated Stripe subscription {stripe_subscription_id} to plan {new_plan.id}"
            )
            return updated_subscription

        except stripe.error.StripeError as e:
            logger.error(
                f"Stripe error updating subscription {stripe_subscription_id}: {e}"
            )
            if "No such subscription" in str(e):
                raise NotFoundError(f"Stripe subscription {stripe_subscription_id} not found")
            raise ValidationError(f"Failed to update subscription: {str(e)}")

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Stripe webhook signature.

        Args:
            payload: Raw request payload
            signature: Stripe signature from header

        Returns:
            True if signature is valid, False otherwise
        """
        settings = get_settings()
        if not settings.stripe.webhook_secret:
            logger.warning("Stripe webhook secret not configured. Cannot verify signature.")
            return False

        try:
            stripe.Webhook.construct_event(
                payload,
                signature,
                settings.stripe.webhook_secret,
            )
            return True
        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"Stripe webhook signature verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error verifying Stripe webhook signature: {e}")
            return False

    async def get_subscription(self, stripe_subscription_id: str) -> Dict[str, Any]:
        """
        Get Stripe subscription by ID.

        Args:
            stripe_subscription_id: Stripe subscription ID

        Returns:
            Stripe subscription object as dictionary

        Raises:
            NotFoundError: If subscription not found
            ValidationError: If Stripe is not configured
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot retrieve subscription.")

        try:
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving subscription {stripe_subscription_id}: {e}")
            if "No such subscription" in str(e):
                raise NotFoundError(f"Stripe subscription {stripe_subscription_id} not found")
            raise ValidationError(f"Failed to retrieve subscription: {str(e)}")

    async def get_customer(self, stripe_customer_id: str) -> Dict[str, Any]:
        """
        Get Stripe customer by ID.

        Args:
            stripe_customer_id: Stripe customer ID

        Returns:
            Stripe customer object as dictionary

        Raises:
            NotFoundError: If customer not found
            ValidationError: If Stripe is not configured
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot retrieve customer.")

        try:
            customer = stripe.Customer.retrieve(stripe_customer_id)
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving customer {stripe_customer_id}: {e}")
            if "No such customer" in str(e):
                raise NotFoundError(f"Stripe customer {stripe_customer_id} not found")
            raise ValidationError(f"Failed to retrieve customer: {str(e)}")

    async def end_trial_early(
        self, stripe_subscription_id: str, reason: str = "usage_limit_reached"
    ) -> Dict[str, Any]:
        """
        End a Stripe subscription trial early.

        This immediately ends the trial period and charges the customer.
        Useful when usage limits (e.g., 200 minutes) are reached before the trial period ends.

        Args:
            stripe_subscription_id: Stripe subscription ID
            reason: Reason for ending trial early (for logging)

        Returns:
            Updated Stripe subscription object as dictionary

        Raises:
            NotFoundError: If subscription not found
            ValidationError: If Stripe is not configured or operation fails
        """
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise ValidationError("Stripe is not configured. Cannot end trial early.")

        try:
            # Get current subscription to check trial status
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)

            # Check if subscription is in trial
            if subscription.get("status") != "trialing":
                logger.warning(
                    f"Subscription {stripe_subscription_id} is not in trial status "
                    f"(status: {subscription.get('status')})"
                )
                return subscription

            # End trial immediately by setting trial_end to now
            # Stripe will charge the customer right away
            updated_subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                trial_end="now",  # End trial immediately
                metadata={
                    **subscription.get("metadata", {}),
                    "trial_ended_early": "true",
                    "trial_end_reason": reason,
                },
            )

            logger.info(
                f"Ended trial early for Stripe subscription {stripe_subscription_id}. "
                f"Reason: {reason}"
            )
            return updated_subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error ending trial early for {stripe_subscription_id}: {e}")
            if "No such subscription" in str(e):
                raise NotFoundError(f"Stripe subscription {stripe_subscription_id} not found")
            raise ValidationError(f"Failed to end trial early: {str(e)}")


def get_stripe_service(session: AsyncSession) -> StripeService:
    """
    Factory function to create StripeService instance.

    Args:
        session: Database session

    Returns:
        StripeService instance
    """
    return StripeService(session)
