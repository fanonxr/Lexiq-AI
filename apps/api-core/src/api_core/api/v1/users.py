"""User management endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_core.auth.dependencies import get_current_active_user, require_permissions
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import NotFoundError, ValidationError
from api_core.models.user import UserListResponse, UserProfileUpdate, UserResponse
from api_core.services.user_service import get_user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get current user profile.

    Returns the profile of the currently authenticated user.
    """
    try:
        async with get_session_context() as session:
            user_service = get_user_service(session)
            
            # Try to get user by ID (database UUID)
            user = await user_service.get_user_by_id(current_user.user_id)
            db_user = None
            
            if user:
                # User found by database ID
                db_user = await user_service.repository.get_by_id(current_user.user_id)
            elif current_user.token_type == "azure_ad_b2c" and current_user.user_info:
                # Fallback: If user not found by ID, try Azure AD object ID
                # This handles cases where auto-sync failed or user_id is still Azure AD object ID
                azure_ad_object_id = current_user.user_info.oid
                if azure_ad_object_id:
                    logger.debug(
                        f"User not found by ID {current_user.user_id}, "
                        f"trying Azure AD object ID: {azure_ad_object_id}"
                    )
                    db_user = await user_service.repository.get_by_azure_ad_object_id(
                        azure_ad_object_id
                    )
                    
                    if db_user:
                        # User found by Azure AD object ID - sync might have failed earlier
                        # Try to sync again to ensure user is up to date
                        try:
                            email = current_user.user_info.email or current_user.email
                            name = current_user.user_info.display_name or current_user.user_info.name or email.split("@")[0]
                            tenant_id = current_user.user_info.tenant_id
                            
                            user_profile = await user_service.sync_user_from_azure_ad(
                                azure_ad_object_id=azure_ad_object_id,
                                email=email,
                                name=name,
                                azure_ad_tenant_id=tenant_id,
                            )
                            db_user = await user_service.repository.get_by_id(user_profile.id)
                            logger.info(
                                f"Successfully synced user on fallback: {user_profile.id}"
                            )
                        except Exception as sync_error:
                            logger.warning(
                                f"Failed to sync user on fallback: {sync_error}, "
                                f"using existing user record"
                            )
                            # Continue with existing user
            
            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found",
                )

            # If user doesn't have a firm_id, create one for them
            if not db_user.firm_id:
                from api_core.repositories.firms_repository import FirmsRepository
                firms_repo = FirmsRepository(session)
                
                # Create a firm for the user
                firm = await firms_repo.create(
                    name=f"{db_user.name}'s Firm",  # Default firm name
                )
                db_user.firm_id = firm.id
                await session.flush()
                await session.refresh(db_user)
                logger.info(f"Created firm {firm.id} for existing user {db_user.id}")

            return user_service._user_to_response(db_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user profile",
        )


@router.put("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Update current user profile.

    Allows users to update their own profile information.
    """
    try:
        async with get_session_context() as session:
            user_service = get_user_service(session)

            # Convert Pydantic model to dict, excluding None values
            update_dict = profile_data.model_dump(exclude_unset=True)

            # Update user profile
            await user_service.update_user_profile(
                current_user.user_id, **update_dict
            )

            # Get updated user
            db_user = await user_service.repository.get_by_id(current_user.user_id)
            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found",
                )

            return user_service._user_to_response(db_user)
    except ValidationError as e:
        logger.warning(f"Profile update validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating user profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating user profile",
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_id(
    user_id: str,
    current_user: TokenValidationResult = Depends(require_permissions(["admin:read"])),
):
    """
    Get user by ID (admin only).

    Returns user profile for the specified user ID.
    Requires admin permissions.
    """
    try:
        async with get_session_context() as session:
            user_service = get_user_service(session)
            user = await user_service.get_user_by_id(user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found",
                )

            # Get full user model for UserResponse
            db_user = await user_service.repository.get_by_id(user_id)
            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found",
                )

            return user_service._user_to_response(db_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user",
        )


@router.get("", response_model=UserListResponse, status_code=status.HTTP_200_OK)
async def list_users(
    query: Optional[str] = Query(None, description="Search query (name or email)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: TokenValidationResult = Depends(require_permissions(["admin:read"])),
):
    """
    List users with pagination and filtering (admin only).

    Returns a paginated list of users with optional filtering.
    Requires admin permissions.
    """
    try:
        async with get_session_context() as session:
            user_service = get_user_service(session)

            # Search users
            users = await user_service.search_users(
                query=query,
                is_active=is_active,
                is_verified=is_verified,
                skip=skip,
                limit=limit,
            )

            # Get total count (simplified - count all if no filters)
            # Note: For query-based search, we'd need a more complex count query
            # For now, we'll use the length of results as an approximation
            if query:
                # If there's a query, we can't easily count without running the search
                # So we'll approximate with the result count
                total = len(users)
            else:
                # Count with filters
                filters = {}
                if is_active is not None:
                    filters["is_active"] = is_active
                if is_verified is not None:
                    filters["is_verified"] = is_verified
                total = await user_service.repository.count(filters if filters else None)

            # Get full user models for UserResponse
            db_users = []
            for user_profile in users:
                db_user = await user_service.repository.get_by_id(user_profile.id)
                if db_user:
                    db_users.append(db_user)

            # Convert to UserResponse list
            user_responses = [
                user_service._user_to_response(db_user) for db_user in db_users
            ]

            return UserListResponse(
                users=user_responses,
                total=total,
                skip=skip,
                limit=limit,
            )
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing users",
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_user(
    user_id: str,
    current_user: TokenValidationResult = Depends(require_permissions(["admin:delete"])),
):
    """
    Deactivate a user account (admin only).

    Deactivates the user account instead of deleting it.
    Requires admin permissions.
    """
    try:
        async with get_session_context() as session:
            user_service = get_user_service(session)

            # Prevent self-deactivation
            if user_id == current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate your own account",
                )

            # Deactivate user
            await user_service.deactivate_user(user_id)

            return None  # 204 No Content
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deactivating user",
        )
