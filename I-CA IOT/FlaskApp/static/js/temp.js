let aliveSecond = 0;
let heartBeatRate = 1000;
let pubnub;
let appChannel = "Tempify";
let ttl = 60;

const setupPubNub = () => {
    pubnub = new PubNub({
        publishKey: 'pub-c-5253f8ef-b7b9-415f-8dea-b1f2480e887d',
        subscribeKey: 'sub-c-cf8e1959-db2f-4db9-a46a-429895791f16',
        userId: 'martin123'
    });
    console.log("Checking PubNub:   ", pubnub)
    
    const channel = pubnub.channel(appChannel);
    
    const subscription = channel.subscription();
    
    pubnub.addListener({
        status: (s) =>{
            console.log("Status", s.category);
            console.log("Message", s.message);
        },
        message: (event) => {
            console.log("Messages", event.message);
            const PI_response = event.message;
            const time_value = PI_response.time_taken;
            const temp_value = PI_response.temperature_value;
            const humidity_value = PI_response.humidity_value;
            const soil_value = PI_response.soil_value;
            console.log("time", time_value, "temp", temp_value, "humidity", humidity_value, "soil" , soil_value)
        }
    });

    subscription.onMessage = (messageEvent) => {
        handleMessage(messageEvent.message);
    };

    console.log("channel:", channel)
    subscription.subscribe();
};

function handleMessage(message)
{
    console.log("message here",message.temperature_value)
    if(message.temperature_value > 0 || message.temperature_value < 100)
    {
        document.getElementById("temp").innerHTML = message.temperature_value;
    }
    if(message.temperature_value < 0 || message.temperature_value > 100)
    {
        document.getElementById("temp").innerHTML = "ERROR";
    }
}

const publishMessage = async(message) => {
    const publishPayload = {
        channel: appChannel,
        message: {
            message:message
        },
    };
    await pubnub.publish(publishPayload);
}