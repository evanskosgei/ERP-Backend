from flask import request, Response, json, jsonify
from main import mysql, app
from resources.logs.logger import ErrorLogger
from resources.payload.payload import Localtime
from resources.transactions.bookkeeping import DebitCredit
import uuid

class CashStockPurchase():
          
    def create_cash_stock_purchase(self, user):
        #Get the request data 
        request_data = request.get_json()       
        
        validated_data = request_data
        # validated_data, error_messages = self.reg_supplier.serialize_register_data(data)
        # if error_messages:
        #     return jsonify({"error": error_messages}), 400
        
        total_amount = float(validated_data["total_amount"].replace(",", ""))
        # supplier_name = validated_data["supplier_name"]
        supplier_id = validated_data["supplier_id"]
        supplier_payable_account_number = validated_data["supplier_payable_account_number"]
        bank_account_number = validated_data["bank_account_number"]
        purchase_date = validated_data["purchase_date"]
              
        product_details = json.dumps(validated_data["product_details"])
        notes = validated_data["notes"] 
        transaction_id = validated_data["transaction_id"] 
        
        # Open A connection to the database
        try:
            cur =  mysql.get_db().cursor()
        except:
            message = {'status':500,
                       'error':'sp_a11',
                       'description':"Couldn't connect to the Database!"}
            ErrorLogger().logError(message)
            return message, 500
        #Save data to the database
        
        try:
            status = 2 #pending approval
            delivery_status = 1 #pending delivery 
            quantity_delivered = 0
            created_date = Localtime().gettime()
            created_by = user['id']
            
            trans_uuid_ = str(uuid.uuid4())
            trans_uuid = trans_uuid_.replace("-", "" )
            trans_uuid = str(trans_uuid)
            global_id = 'zz' + str(trans_uuid[-12:])
        
            #store cash stock purchased details
            cur.execute("""INSERT INTO cash_stock_purchases (global_id, total_amount, transaction_id, supplier_id, supplier_payable_account_number, bank_account_number ,purchase_date, delivery_status, notes, created_date, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                                                            (global_id, total_amount, transaction_id, supplier_id, supplier_payable_account_number, bank_account_number ,purchase_date, delivery_status, notes, created_date, created_by, status))
            mysql.get_db().commit()
            rowcount = cur.rowcount
            if rowcount:
                cash_stock_purchase_id = str(cur.lastrowid)
                
                phone_model_details = json.loads(product_details)                
                for phone_model_detail in phone_model_details:

                    model_id = phone_model_detail["model_id"]
                    quantity = phone_model_detail["quantity"]
                    price_per_unit = float(phone_model_detail["price_per_unit"].replace(",", ""))
                    total_amount_per_model = float(phone_model_detail["total_amount_per_model"].replace(",", ""))
                
                    cur.execute("""INSERT INTO cash_stock_purchase_models (cash_stock_purchase_id, global_id, model_id, price_per_unit, quantity, quantity_delivered, total_amount_per_model, created_date, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                                                                          (cash_stock_purchase_id, global_id, model_id, price_per_unit, quantity, quantity_delivered, total_amount_per_model, created_date, created_by, status))
                    mysql.get_db().commit()
            else:
                message = {"description":"Failed to capture stock product details",
                           "status":201}
                return message
                
            message = {"description":"Cash stock purchase transaction was created successfully",
                       "status":200}
            return message
                        

        #Error handling
        except Exception as error:
            message = {'status':501, 
                       'error':'sp_a02',
                       'description':'Failed to create cash stock purchase transaction. Error description ' + format(error)}
            ErrorLogger().logError(message)
            return jsonify(message), 501  
        finally:
            cur.close()
  
    def list_cash_stock_purchase(self, user):
        
        request_data = request.get_json() 
        
        if request_data == None:
            message = {'status':402,
                       'error':'sp_a03',
                       'description':'Request data is missing some details!'}
            ErrorLogger().logError(message)
            return jsonify(message)
       
        try:
            cur = mysql.get_db().cursor()
                    
        except:
            message = {'status':500,
                        'error':'sp_a14',
                        'description':"Couldn't connect to the Database!"}
            ErrorLogger().logError(message)
            return message
                
        try:
            status = request_data["status"]
            
            cur.execute("""SELECT id, global_id, transaction_id, total_amount, supplier_id, supplier_payable_account_number, bank_account_number, purchase_date, delivery_status, notes, created_date, created_by FROM cash_stock_purchases WHERE status = %s """, (status))
            purchases = cur.fetchall()            
            if purchases:
                response_array = []
                
                for purchase in purchases:
                    cash_stock_purchase_id = purchase["id"]
                    global_id = purchase["global_id"]
                    user_id = purchase["created_by"]
                    supplier_id = purchase['supplier_id']
                    
                    cur.execute("""SELECT first_name, last_name from user_details WHERE user_id = %s """, (user_id))
                    get_user = cur.fetchone()
                    if get_user:
                        first_name = get_user["first_name"]
                        last_name = get_user["last_name"]
                        user_name = first_name + '' + last_name
                    else:
                        user_name = ''
                        
                    cur.execute("""SELECT business_name from suppliers WHERE id = %s """, (supplier_id))
                    get_supplier = cur.fetchone()
                    if get_supplier:
                        supplier_business_name = get_supplier["business_name"]
                    else:
                        supplier_business_name = ''
                    
                    product_details = []
                    cur.execute("""SELECT id, model_id,  price_per_unit, quantity, quantity_delivered, total_amount_per_model FROM cash_stock_purchase_models WHERE cash_stock_purchase_id = %s AND status = %s""", (cash_stock_purchase_id, status))
                    models_purchased = cur.fetchall()
                    if models_purchased:
                        for model_purchased in models_purchased:
                    
                            model_details = {
                                "model_id":model_purchased["model_id"],
                                "price_per_unit":float(model_purchased["price_per_unit"]),
                                "quantity":float(model_purchased["quantity"]),
                                "quantity_delivered":float(model_purchased["quantity_delivered"]),
                                "total_amount_per_model":float(model_purchased["total_amount_per_model"])
                            }
                            product_details.append(model_details)
                    
                    response = {
                        
                        "id": purchase['id'],
                        "total_amount": float(purchase['total_amount']),
                        "transaction_id": purchase["transaction_id"],
                        "supplier_name": supplier_business_name,
                        "supplier_id": supplier_id,
                        "supplier_payable_account_number": purchase['supplier_payable_account_number'],
                        "bank_account_number": purchase['bank_account_number'],
                        "purchase_date": purchase['purchase_date'],
                        "product_details":product_details,
                        "delivery_status": purchase['delivery_status'],
                        "notes": purchase['notes'],
                        "created_date": purchase['created_date'],
                        "created_by_id": purchase['created_by'],
                        "user_name":user_name
                        
                    }
                    response_array.append(response)
            
                message = {'status':200,
                            'response':response_array, 
                            'description':'Cash stock purchase records were fetched successfully!'
                        }   
                return jsonify(message), 200
            
            else:                
                message = {'status':201,
                            'error':'sp_a04',
                            'description':'Failed to fetch cash stock purchase !'
                        }   
                return jsonify(message), 201             
             
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a05',
                       'description':'Failed to retrieve cash stock purchase record from database.' + format(error)}
            ErrorLogger().logError(message),
            return jsonify(message), 501  
        finally:
            cur.close()
        
    def get_cash_stock_purchase_details(self, user):
        
        request_data = request.get_json() 
        
        if request_data == None:
            message = {'status':402,
                       'error':'sp_a03',
                       'description':'Request data is missing some details!'}
            ErrorLogger().logError(message)
            return jsonify(message), 402
        
        id = request_data["id"]
        
        try:
            cur = mysql.get_db().cursor()
                    
        except:
            message = {'status':500,
                        'error':'sp_a14',
                        'description':"Couldn't connect to the Database!"}
            ErrorLogger().logError(message)
            return message, 500
                
        try:
        
            cur.execute("""SELECT id, transaction_id, total_amount, supplier_name, supplier_id, supplier_payable_account_number, bank_account_number, purchase_date, delivery_status, notes, created_date, created_by FROM cash_stock_purchases WHERE id = %s """, (id))
            purchase = cur.fetchone()            
            if purchase:
                cash_stock_purchase_id = purchase["id"]
                user_id = purchase["created_by"]
                supplier_id = purchase['supplier_id']
                
                cur.execute("""SELECT first_name, last_name from user_details WHERE user_id = %s """, (user_id))
                get_user = cur.fetchone()
                if get_user:
                    first_name = get_user["first_name"]
                    last_name = get_user["last_name"]
                    user_name = first_name + '' + last_name
                else:
                    user_name = ''
                    
                cur.execute("""SELECT business_name from suppliers WHERE id = %s """, (supplier_id))
                get_supplier = cur.fetchone()
                if get_supplier:
                    supplier_business_name = get_supplier["business_name"]
                else:
                    supplier_business_name = ''
                    
                product_details = []
                cur.execute("""SELECT id, model_id,  price_per_unit,  quantity, quantity_delivered, total_amount_per_model FROM cash_stock_purchase_models WHERE cash_stock_purchase_id = %s """, (cash_stock_purchase_id))
                models_purchased = cur.fetchall()
                if models_purchased:
                    for model_purchased in models_purchased:
                
                        model_details = {
                            "model_id":model_purchased["model_id"],
                            "price_per_unit":float(model_purchased["price_per_unit"]),
                            "quantity":float(model_purchased["quantity"]),
                            "quantity_delivered":float(model_purchased["quantity_delivered"]),
                            "total_amount_per_model":float(model_purchased["total_amount_per_model"])
                        }
                        product_details.append(model_details)
                            
                response = {
                    
                    "id": purchase['id'],
                    "transaction_id": purchase['transaction_id'],
                    "supplier_name": supplier_business_name,
                    "total_amount": float(purchase['total_amount']),
                    "supplier_name": purchase['supplier_name'],
                    "supplier_id": purchase['supplier_id'],
                    "supplier_payable_account_number": purchase['supplier_payable_account_number'],
                    "bank_account_number": purchase['bank_account_number'],
                    "purchase_date": purchase['purchase_date'],
                    "product_details":product_details,
                    "delivery_status": purchase['delivery_status'],
                    "notes": purchase['notes'],
                    "created_date": purchase['created_date'],
                    "created_by_id": purchase['created_by'],
                    "user_name":user_name
                }
                
                return response
                
            else:                
                message = {'status':201,
                            'error':'sp_a04',
                            'description':'Failed to fetch cash stock purchase records!'
                        }   
                return jsonify(message), 201             
             
            
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a05',
                       'description':'Failed to retrieve cash stock purchase record from database.' + format(error)}
            ErrorLogger().logError(message),
            return jsonify(message), 501
        finally:
            cur.close()
             
    def approve_cash_stock_purchase(self, user):
        request_data = request.get_json() 
               
        if request_data == None:
            message = {'status':402,
                       'error':'sp_a06',
                       'description':'Request data is missing some details!'}
            ErrorLogger().logError(message)
            return jsonify(message)

        id = request_data["id"]
        
        try:
            cur = mysql.get_db().cursor()
        except:
            message = {'status':500,
                       'error':'sp_a07',
                       'description':"Couldn't connect to the Database!"}
            ErrorLogger().logError(message)
            return jsonify(message)

        try:  
            #fetch cash stock purchase details
            cur.execute("""SELECT id, global_id, transaction_id, total_amount, supplier_name, supplier_id, supplier_payable_account_number, bank_account_number, purchase_date, delivery_status, notes, created_date, created_by FROM cash_stock_purchases WHERE status =2 AND id = %s """, (id))
            purchase = cur.fetchone()            
            if purchase:
                id = purchase["id"]
                global_id = purchase["global_id"]
                transaction_id = purchase["transaction_id"]
                total_amount = float(purchase["total_amount"])
                supplier_id = purchase["supplier_id"]
                supplier_payable_account_number = purchase["supplier_payable_account_number"]
                bank_account_number = purchase["bank_account_number"]
                purchase_date = purchase["purchase_date"]
                
                product_details = []
                cur.execute("""SELECT id, model_id, price_per_unit, quantity, quantity_delivered, total_amount_per_model FROM cash_stock_purchase_models WHERE global_id = %s """, (global_id))
                models_purchased = cur.fetchall()
                if models_purchased:
                    for model_purchased in models_purchased:
                
                        model_details = {
                            "model_id":model_purchased["model_id"],
                            "price_per_unit":float(model_purchased["price_per_unit"]),
                            "quantity":float(model_purchased["quantity"]),
                            "total_amount_per_model":float(model_purchased["total_amount_per_model"]),
                             "quantity_delivered":float(model_purchased["quantity_delivered"]),
                        }
                        product_details.append(model_details)
                
                details = {
                            "id":id,
                            "user_id":user["id"],
                            "global_id":global_id,
                            "bank_account_number":bank_account_number,
                            "payable_account_number":supplier_payable_account_number,
                            "amount":total_amount,                
                            "settlement_date":purchase_date,
                            "transaction_id":transaction_id,
                            "product_details":product_details

                        }
                        
                api_message = DebitCredit().cash_stock_purchase_approve(details)  
                if int(api_message["status"]) == 200:
                    message = {'status':200,
                                'description':'Cash stock purchase record was approved successfully!'}
                    return jsonify(message)  
                else:              
                    return jsonify(api_message)
                
            else:
                message = {'status':201,
                            'description':'Cash stock purchase record was not found!'}
                
                return jsonify(message), 201
                    
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a09',
                       'description':'Failed to approve cash stock purchase record. Error description ' + format(error)}
            ErrorLogger().logError(message)
            return jsonify(message)  
        finally:
            cur.close()

     
    def list_cash_stock_todeliver(self, user):
        
        request_data = request.get_json() 
        
        if request_data == None:
            message = {'status':402,
                       'error':'sp_a03',
                       'description':'Request data is missing some details!'}
            ErrorLogger().logError(message)
            return jsonify(message)
       
        try:
            cur = mysql.get_db().cursor()
                    
        except:
            message = {'status':500,
                        'error':'sp_a14',
                        'description':"Couldn't connect to the Database!"}
            ErrorLogger().logError(message)
            return message
                
        try:
            status = request_data["status"]
            
            response_array = []
            # cur.execute("""SELECT id, global_id, transaction_id, total_amount, supplier_name, supplier_id, supplier_payable_account_number, bank_account_number, purchase_date, delivery_status, notes, created_date, created_by FROM cash_stock_purchases WHERE status = %s """, (status))
            cur.execute("""SELECT cash_stock_purchase_id, SUM(quantity) as total_quantity, SUM(quantity_delivered) as total_quantity_delivered FROM cash_stock_purchase_models WHERE status = %s AND quantity > quantity_delivered GROUP BY cash_stock_purchase_id""", (status,))           
            stock_purchase_models = cur.fetchall()
            if stock_purchase_models:
               
                for row in stock_purchase_models:
                    cash_stock_purchase_id = row["cash_stock_purchase_id"]
                    
                    cur.execute("""SELECT transaction_id, global_id, total_amount, supplier_name, supplier_id, supplier_payable_account_number, bank_account_number, purchase_date, delivery_status, notes, created_date, created_by FROM cash_stock_purchases WHERE id = %s """, (cash_stock_purchase_id))
                    stock_purchases = cur.fetchone() 
                    user_id = stock_purchases["created_by"]
                    supplier_id = stock_purchases['supplier_id']
                    
                    cur.execute("""SELECT first_name, last_name from user_details WHERE user_id = %s """, (user_id))
                    get_user = cur.fetchone()
                    if get_user:
                        first_name = get_user["first_name"]
                        last_name = get_user["last_name"]
                        user_name = first_name + '' + last_name
                    else:
                        user_name = ''
                        
                    cur.execute("""SELECT business_name from suppliers WHERE id = %s """, (supplier_id))
                    get_supplier = cur.fetchone()
                    if get_supplier:
                        supplier_business_name = get_supplier["business_name"]
                    else:
                        supplier_business_name = ''
                    
                    product_details = []
                    cur.execute("""SELECT id, model_id, price_per_unit, quantity, quantity_delivered, total_amount_per_model FROM cash_stock_purchase_models WHERE cash_stock_purchase_id = %s """, (cash_stock_purchase_id))
                    models_purchased = cur.fetchall()
                    if models_purchased:
                        for model_purchased in models_purchased:
                    
                            quantity = float(model_purchased["quantity"])
                            quantity_delivered = float(model_purchased["quantity_delivered"])
                            todeliver = quantity - quantity_delivered
                            if todeliver < 0:
                                to_deliver = 0
                            else:
                                to_deliver = todeliver
                    
                            model_details = {
                                "model_id":model_purchased["model_id"],
                                "price_per_unit":float(model_purchased["price_per_unit"]),
                                "quantity":quantity,
                                "quantity_delivered":quantity_delivered,
                                "to_deliver":to_deliver,
                                "total_amount_per_model":float(model_purchased["total_amount_per_model"])
                            }
                            product_details.append(model_details)
                    
                    response = {
                        
                        "id": cash_stock_purchase_id,
                        "total_amount": float(stock_purchases['total_amount']),
                        "transaction_id": stock_purchases["transaction_id"],
                        "global_id": stock_purchases["global_id"],
                        "supplier_name": supplier_business_name,
                        "supplier_id": supplier_id,
                        "supplier_payable_account_number": stock_purchases['supplier_payable_account_number'],
                        "bank_account_number": stock_purchases['bank_account_number'],
                        "purchase_date": stock_purchases['purchase_date'],
                        "product_details":product_details,
                        "delivery_status": stock_purchases['delivery_status'],
                        "notes": stock_purchases['notes'],
                        "created_date": stock_purchases['created_date'],
                        "created_by_id": stock_purchases['created_by'],
                        "user_name":user_name
                        
                    }
                    response_array.append(response)
            
            
                message = {'status':200,
                            'response':response_array, 
                            'description':'Cash stock purchase pending delivery were fetched successfully!'
                        }   
                return jsonify(message), 200
            
            else:                
                message = {'status':201,
                            'error':'sp_a04',
                            'description':'Failed to fetch cash stock purchase !'
                        }   
                return jsonify(message), 201             
             
            
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a05',
                       'description':'Failed to retrieve cash stock purchase record from database.' + format(error)}
            ErrorLogger().logError(message),
            return jsonify(message), 501 
        finally:
            cur.close()