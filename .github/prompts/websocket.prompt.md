The websocket service will handling real-time communication between client and server

The current websocket service works by periodically broadcast device status to subscribed tenant. This method may ensure consistency but sacrifice responsiveness.

I want to move the event-drivent architecture.

## Involved dependencies:

- `routers/websocket.py`: handle the websocket connection.
- `services/cache_service.py`: cache and retrieve device status and information
- `utils/auth`: validate websocket token

## Work flow

1. The tenant is logged in and subscribe to websocket channel.
2. Each tenant will access to their devices' real-time status.
3. With event-driven, on new incoming data from mqtt, broadcast the device information asynchronosly to subscribe tenant

## Recommendation

- Pub/Sub architecture or callback should be used, the choice depends on your optimization
- Follow SOLID principles, ensure that each function does not collide responsibility with others.
- Ensure consistency and resilient.