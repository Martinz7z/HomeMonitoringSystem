let aliveSecond = 0;
let heartBeatRate = 10000;
let pubnub;
let appChannel = "Tempify";
let ttl = 60;

//sendEvent('get_user_token');


function refreshToken()
{
    console.log("Get user token request");
    sendEvent('get_user_token');
    let refresh_time = (ttl-1)*60*1000;
    console.log(refresh_time);
    setTimeout('refreshToken()', refresh_time);
}

function time()
{
    let d = new Date();
    let currentSecond = d.getTime();
    if(currentSecond - aliveSecond > heartBeatRate + 1000)
    {
        document.getElementById("connection_id").innerHTML="DEAD";
    }
    else
    {
        document.getElementById("connection_id").innerHTML="ALIVE";
    }
    setTimeout('time()', 1000);
}

function keepAlive()
{
    fetch('/keep_alive')
    .then(response=>{
        if(response.ok){
            let date = new Date();
            aliveSecond = date.getTime();
	    return response.json();
        }
        throw new Error('Server offline');
    })
    .catch(error=>console.log(error));
    setTimeout('keepAlive()', heartBeatRate);
}

function handleClick(cb)
{
    if(cb.checked)
    {
        value="on";
    }
    else
    {
        value = "off";
    }
    publishMessage({"buzzer":value});
}

const setupPubNub = () => {
    pubnub = new PubNub({
        publishKey: 'pub-c-5253f8ef-b7b9-415f-8dea-b1f2480e887d',
        subscribeKey: 'sub-c-cf8e1959-db2f-4db9-a46a-429895791f16',
        userId: 'martin123',
        cryptoModule: PubNub.CryptoModule.aesCbcCryptoModule({cipherKey:'sd3b_secret'}),
	//cryptoModule: PubNub.CryptoModule.aesCbcCryptoModule({cipherKey: 'sd3b-secret'})
    });
    //create a local channel
    const channel = pubnub.channel(appChannel);
    //create a subscription on the channel
    const subscription = channel.subscription();
    //add listener
    pubnub.addListener({
        status: (s) =>{
            console.log("Status", s.category);
        },
    });

    //add an onMessage listener on the channel
    subscription.onMessage = (messageEvent) => {
        handleMessage(messageEvent.message);
    };
    //subscribe to the channel
    subscription.subscribe();
};

function handleMessage(message)
{
    if(message == '"Motion":"Yes"')
    {
        document.getElementById("motion_id").innerHTML = "Yes";
    }
    if(message == '"Motion":"No"')
    {
        document.getElementById("motion_id").innerHTML = "No";
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

function logout()
{
    location.replace("/logout");
}

function grantAccess(ab)
{
    var userId = ab.id.split("-")[2];
    var readState = document.getElementById("read-user-"+userId).checked;
    var writeState = document.getElementById("write-user-"+userId).checked;
    sendEvent("grant-"+userId+"-"+readState+"-"+writeState);
}

function sendEvent(value)
{
fetch(value,
{
method:"POST",
})
.then(response => response.json())
.then(responseJson =>{
console.log(responseJson);
if (responseJson.hasOwnProperty('token')) {
// Update UUID and Token
pubnub.setUUID(responseJson.uuid);
pubnub.setToken(responseJson.token);

console.log("Token and UUID updated successfully");
subscribe();
// No need to call subscribe() again
}
});
}

function subscribe()
{
    console.log("Trying to subscribe with token");
    const channel = pubnub.channel(appChannel)
    const subscription = channel.subscription();
    subscription.subscribe();

    console.log("Successfully subscribed with token:", pubnub.getToken());
}

