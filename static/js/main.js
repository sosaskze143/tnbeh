if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/static/js/service-worker.js')
  .then(reg=>console.log('SW registered'))
  .catch(console.error);
}

const btnUser = document.getElementById('btn-user');
const btnAdmin = document.getElementById('btn-admin');

if(btnUser){
  btnUser.addEventListener('click', async ()=>{
    const permission = await Notification.requestPermission();
    if(permission==='granted'){
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly:true,
        applicationServerKey:urlBase64ToUint8Array('MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEULZuTRM2LCUlgzLk14VDDJz30ZA1RjC76JmqZqYdMq6aCpU3DZTpEg06W4iWTocVuxxTtjmELZxKz0DtRJ91Bg==')
      });
      await fetch('/api/subscribe',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(sub.toJSON())
      });
    }
    window.location.href='/user';
  });
}

if(btnAdmin) btnAdmin.addEventListener('click',()=>location.href='/login');

function urlBase64ToUint8Array(base64String){
  const padding='='.repeat((4-base64String.length%4)%4);
  const base64=(base64String+padding).replace(/\-/g,'+').replace(/_/g,'/');
  const rawData=window.atob(base64);
  const outputArray=new Uint8Array(rawData.length);
  for(let i=0;i<rawData.length;i++) outputArray[i]=rawData.charCodeAt(i);
  return outputArray;
}