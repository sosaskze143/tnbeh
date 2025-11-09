self.addEventListener('push', function(event){
  const data = event.data.text();
  const options = {body:data};
  event.waitUntil(self.registration.showNotification('إشعار جديد', options));
});