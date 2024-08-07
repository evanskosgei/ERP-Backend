from flask import request, Response, json, jsonify
from main import mysql, app
from resources.logs.logger import ErrorLogger
from resources.payload.payload import Localtime
from resources.transactions.bookkeeping import DebitCredit
from resources.accounts.accounts_class import Accounts
import uuid

class TransitStock():
          
    def create_stock_transit(self, user):
        #Get the request data 
        request_data = request.get_json()       
        
        validated_data = request_data
        # validated_data, error_messages = self.reg_supplier.serialize_register_data(data)
        # if error_messages:
        #     return jsonify({"error": error_messages}), 400
        
        stock_purchases_id = validated_data["stock_purchases_id"]
        delivery_address = validated_data["delivery_address"]
        delivery_note_number = validated_data["delivery_note_number"]
        recipient_address = validated_data["recipient_address"] 
        recipient_name = validated_data["recipient_name"] 
        recipient_mobile_number = validated_data["recipient_mobile_number"] 
        
        transporter_name = validated_data["transporter_name"] 
        transporter_id = validated_data["transporter_id"] 
        bank_account_number = validated_data["bank_account_number"] 
        
        transporter_cost = float(validated_data["transporter_cost"].replace(",", ""))
        delivery_date = validated_data["delivery_date"]
        
        transport_mode = validated_data["transport_mode"] 
        registration_number = validated_data["registration_number"] 
        contact_name = validated_data["contact_name"] 
        contact_number = validated_data["contact_number"] 
        
        stock_state = 1 #not received       
        product_details = json.dumps(validated_data["product_details"])
        notes = validated_data["notes"] 
        
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
            created_date = Localtime().gettime()
            created_by = user['id']
                        
            #fetch cash stock purchased details
            cur.execute("""SELECT global_id FROM cash_stock_purchases WHERE id = %s """, (stock_purchases_id))
            purchased = cur.fetchone()            
            if purchased:
                global_id = purchased["global_id"]
            else:
                message = {"description":"Global id not fetched for cash stock purchased",
                           "status":201}
                return message
        
           
            get_transport_payable_account = Accounts().get_transport_payable_account()
            if int(get_transport_payable_account["status"]) == 200:
                transporter_payable_account_number = get_transport_payable_account["data"]
            else:
                transporter_payable_account_number = ''
                message = {'status':402,
                            'description':"Couldn't fetch transport payabale account!"}
                ErrorLogger().logError(message)                                
                return message
                    
            #put stock in transit
            cur.execute("""INSERT INTO products_in_transit (global_id, stock_purchases_id, delivery_address, delivery_note_number, delivery_date, recipient_address, recipient_name ,recipient_mobile_number, transporter_name, transporter_id, bank_account_number, transporter_payable_account_number, transporter_cost, transport_mode, registration_number, contact_name, contact_number, stock_state, notes, created_date, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                                                           (global_id, stock_purchases_id, delivery_address, delivery_note_number, delivery_date, recipient_address, recipient_name ,recipient_mobile_number, transporter_name, transporter_id, bank_account_number, transporter_payable_account_number, transporter_cost, transport_mode, registration_number, contact_name, contact_number, stock_state, notes, created_date, created_by, status))
            mysql.get_db().commit()
            rowcount = cur.rowcount
            if rowcount:
                products_in_transit_id = str(cur.lastrowid)
                
                phone_model_details = json.loads(product_details)                
                for phone_model_detail in phone_model_details:

                    model_id = phone_model_detail["model_id"]
                    quantity = phone_model_detail["quantity"]
                    
                    quantity_received = 0
                    status = 2
                    cur.execute("""INSERT INTO products_in_transit_models (products_in_transit_id, global_id, model_id, quantity, quantity_received, status) VALUES (%s, %s, %s, %s, %s, %s)""", 
                                                                          (products_in_transit_id, global_id, model_id, quantity, quantity_received, status))
                    mysql.get_db().commit()
            else:
                message = {"description":"Failed to put purchased stock in transit",
                           "status":201}
                return message
                
            message = {"description":"Transit stock was created successfully",
                       "status":200}
            return message
                        

        #Error handling
        except Exception as error:
            message = {'status':501, 
                       'error':'sp_a02',
                       'description':'Failed to create transit stock. Error description ' + format(error)}
            ErrorLogger().logError(message)
            return jsonify(message), 501  
        finally:
            cur.close()
  
    def list_stock_transit(self, user):
        
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
            
            cur.execute("""SELECT id, global_id, stock_purchases_id, delivery_address, delivery_note_number, delivery_date, recipient_address, recipient_name, recipient_mobile_number, transporter_name, transporter_id, bank_account_number, transporter_payable_account_number, transporter_cost, transport_mode, registration_number, contact_name, contact_number, stock_state, notes, created_date, created_by FROM products_in_transit WHERE status = %s """, (status))
            transits = cur.fetchall()            
            if transits:
                response_array = []
                
                for transit in transits:
                    id = transit["id"]
                    global_id = transit["global_id"]
                    created_by = transit["created_by"]
                    stock_purchases_id = transit["stock_purchases_id"] 
                    transporter_id = transit["transporter_id"]
                    transporter_payable_account_number = transit["transporter_payable_account_number"]
                    bank_account_number = transit["bank_account_number"]
                    stock_state = transit["stock_state"]
                    if int(stock_state) ==1:
                        this_stock_state = "In Transit"
                    else:
                        this_stock_state = "Received" 
                        
                    transport_mode = transit["transport_mode"]
                    
                    cur.execute("""SELECT id, name FROM transport_modes WHERE id = %s """, (transport_mode))
                    transport_modes = cur.fetchone()
                    if transport_modes:
                        modeof_transport = transport_modes['name']
                    else:
                        modeof_transport = ''
                        
                    cur.execute("""SELECT id, first_name, last_name FROM user_details WHERE user_id = %s """, (created_by))
                    user_details = cur.fetchone()
                    if user_details:
                        first_name = user_details['first_name']
                        last_name = user_details['last_name']
                        user_name = first_name + '' + last_name
                    else:
                        user_name = ''
                    
                    cur.execute("""SELECT id, name FROM accounts WHERE number = %s """, (transporter_payable_account_number))
                    transporter_acc = cur.fetchone()
                    if transporter_acc:
                        transport_account = transporter_acc['name']
                    else:
                        transport_account = ''
                        
                    cur.execute("""SELECT id, name FROM accounts WHERE number = %s """, (bank_account_number))
                    bank_acc = cur.fetchone()
                    if bank_acc:
                        bank_account = bank_acc['name']
                    else:
                        bank_account = ''
                    
                    product_details = []
                    cur.execute("""SELECT id, model_id, quantity, quantity_received FROM products_in_transit_models WHERE products_in_transit_id = %s """, (id))
                    modelsin_transit = cur.fetchall()
                    if modelsin_transit:
                        for transit_model in modelsin_transit:
                            quantity = float(transit_model["quantity"])
                            quantity_received = float(transit_model["quantity_received"])
                            
                            pending_intransit = quantity - quantity_received
                            if pending_intransit <0:
                                pending_intransit = 0
                            
                            
                            model_details = {
                                "model_id":transit_model["model_id"],
                                "quantity":quantity,
                                "quantity_received":quantity_received,
                                "pending_intransit":pending_intransit
                            }
                            product_details.append(model_details)
                    
                    response = {
                        
                        "id": transit['id'],
                        "global_id": transit['global_id'],
                        "stock_purchases_id": stock_purchases_id,
                        "delivery_address": transit['delivery_address'],
                        "delivery_note_number": transit['delivery_note_number'],
                        "recipient_address": transit['recipient_address'],
                        "recipient_name": transit['recipient_name'],
                        "product_details":product_details,
                        "recipient_mobile_number": transit['recipient_mobile_number'],
                        "delivery_date": transit['delivery_date'],
                        "transporter_name": transit['transporter_name'],
                        "transporter_cost": float(transit['transporter_cost']),
                        "transport_mode": transit['transport_mode'],
                        "transport_mode_name":modeof_transport,
                        "bank_account":bank_account,
                        "transport_account":transport_account,
                        "registration_number": transit['registration_number'],
                        "contact_name": transit['contact_name'],
                        "contact_number": transit['contact_number'],
                        "notes": transit['notes'],
                        "state":this_stock_state,
                        "created_date": transit['created_date'],
                        "created_by_id": transit['created_by'],
                        "user_name":user_name
                        
                    }
                    response_array.append(response)
            
            
                message = {'status':200,
                            'response':response_array, 
                            'description':'Products in transit records were fetched successfully!'
                        }   
                return jsonify(message), 200
            
            else:                
                message = {'status':201,
                            'error':'sp_a04',
                            'description':'Failed to fetch products in transit !'
                        }   
                return jsonify(message), 201             
             
            
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a05',
                       'description':'Failed to retrieve products in transit record from database.' + format(error)}
            ErrorLogger().logError(message),
            return jsonify(message), 501  
        finally:
            cur.close()
        
    def get_stock_transit_details(self, user):
        
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
            
            cur.execute("""SELECT id, global_id, stock_purchases_id, delivery_address, delivery_note_number, delivery_date, recipient_address, recipient_name, recipient_mobile_number, transporter_name, transporter_id, bank_account_number, transporter_payable_account_number, transporter_cost, transport_mode, registration_number, contact_name, contact_number, stock_state, notes, created_date, created_by FROM products_in_transit WHERE id = %s """, (id))
            transit = cur.fetchone()            
            if transit:
                
                global_id = transit["global_id"]
                stock_purchases_id = transit["stock_purchases_id"] 
                transporter_id = transit["transporter_id"]
                transporter_payable_account_number = transit["transporter_payable_account_number"]
                bank_account_number = transit["bank_account_number"]
                created_by = transit["created_by"]
                stock_state = transit["stock_state"]
                if int(stock_state) ==1:
                    this_stock_state = "In Transit"
                else:
                    this_stock_state = "Received"
                
                cur.execute("""SELECT id, name FROM accounts WHERE number = %s """, (transporter_payable_account_number))
                transporter_acc = cur.fetchone()
                if transporter_acc:
                    
                    transport_account = transporter_acc['name']
                else:
                    transport_account = ''
                    
                cur.execute("""SELECT id, first_name, last_name FROM user_details WHERE user_id = %s """, (created_by))
                user_details = cur.fetchone()
                if user_details:
                    first_name = user_details['first_name']
                    last_name = user_details['last_name']
                    user_name = first_name + '' + last_name
                else:
                    user_name = ''
                
                cur.execute("""SELECT id, name FROM accounts WHERE number = %s """, (bank_account_number))
                bank_acc = cur.fetchone()
                if bank_acc:
                    bank_account = bank_acc['name']
                else:
                    bank_account = ''
                
                transport_mode = transit["transport_mode"]
                    
                cur.execute("""SELECT id, name FROM transport_modes WHERE id = %s """, (transport_mode))
                transport_modes = cur.fetchone()
                if transport_modes:
                    modeof_transport = transport_modes['name']
                else:
                    modeof_transport = ''
                        
                product_details = []
                cur.execute("""SELECT id, model_id, quantity FROM products_in_transit_models WHERE global_id = %s """, (global_id))
                modelsin_transit = cur.fetchall()
                if modelsin_transit:
                    for transit_model in modelsin_transit:
                
                        model_details = {
                            "model_id":transit_model["model_id"],
                            "quantity":float(transit_model["quantity"]),
                        }
                        product_details.append(model_details)
                
                response = {
                    
                    "id": transit['id'],
                    "global_id": transit['global_id'],
                    "stock_purchases_id": stock_purchases_id,
                    "delivery_address": transit['delivery_address'],
                    "delivery_date": transit['delivery_date'],
                    "delivery_note_number": transit['delivery_note_number'],
                    "recipient_address": transit['recipient_address'],
                    "recipient_name": transit['recipient_name'],
                    "product_details":product_details,
                    "recipient_mobile_number": transit['recipient_mobile_number'],
                    "transporter_name": transit['transporter_name'],
                    "transporter_cost": float(transit['transporter_cost']),
                    "transport_mode": transit['transport_mode'],
                    "transport_mode_name":modeof_transport,
                    "bank_account":bank_account,
                    "transport_account":transport_account,
                    "registration_number": transit['registration_number'],
                    "contact_name": transit['contact_name'],
                    "contact_number": transit['contact_number'],
                    "notes": transit['notes'],
                    "state":this_stock_state,
                    "created_date": transit['created_date'],
                    "created_by_id": transit['created_by'],
                    "user_name":user_name
                    
                }
            
                return response
                
            else:                
                message = {'status':201,
                            'error':'sp_a04',
                            'description':'Failed to fetch stock in transit details!'
                        }   
                return jsonify(message), 201             
             
            
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a05',
                       'description':'Failed to fetch stock in transit details.' + format(error)}
            ErrorLogger().logError(message),
            return jsonify(message), 501
        finally:
            cur.close()
             
    def approve_stock_transit(self, user):
        request_data = request.get_json() 
               
        if request_data == None:
            message = {'status':402,
                       'error':'sp_a06',
                       'description':'Request data is missing some details!'}
            ErrorLogger().logError(message)
            return jsonify(message)

        id = request_data["id"]

        approved_by = user["id"]
        dateapproved = Localtime().gettime()
        
        try:
            cur = mysql.get_db().cursor()
        except:
            message = {'status':500,
                       'error':'sp_a07',
                       'description':"Couldn't connect to the Database!"}
            ErrorLogger().logError(message)
            return jsonify(message)

        try:  
            #update cash stock purchase details
            cur.execute("""SELECT id, stock_purchases_id, global_id, delivery_note_number, transporter_cost, transporter_payable_account_number, bank_account_number, delivery_date FROM products_in_transit WHERE status = 2 AND id = %s """, (id))
            purchase = cur.fetchone()            
            if purchase:
                
                
                stock_purchases_id = purchase["stock_purchases_id"]
                global_id = purchase["global_id"]
                transaction_id = purchase["delivery_note_number"]
                total_amount = float(purchase["transporter_cost"])
                transporter_payable_account_number = purchase["transporter_payable_account_number"]
                bank_account_number = purchase["bank_account_number"]
                delivery_date = purchase["delivery_date"]
                
                #If there was transport cose, record the expense
                if total_amount > 0:
                    details = {
                                "id":id,
                                "user_id":user["id"],
                                "global_id":global_id,
                                "bank_account_number":bank_account_number,
                                "payable_account_number":transporter_payable_account_number,
                                "amount":total_amount,                
                                "settlement_date":delivery_date,
                                "transaction_id":transaction_id
                            }
                            
                    api_message = DebitCredit().transit_stock_approve(details)  
                else:
                    pass
                
                #update transit record
                cur.execute("""UPDATE products_in_transit set status=1, approved_date = %s, approved_by = %s WHERE id = %s """, ([dateapproved, approved_by, id]))
                mysql.get_db().commit() 
                rowcount = cur.rowcount
                if rowcount:
                    
                    cur.execute("""UPDATE products_in_transit_models set status=1 WHERE products_in_transit_id = %s """, (id))
                    mysql.get_db().commit() 
                        
                    #For each model placed in transit, update purchases records to indicated number of models delivered
                    cur.execute("""SELECT model_id, quantity FROM products_in_transit_models WHERE products_in_transit_id = %s """, (id))
                    modelsin_transit = cur.fetchall()
                    if modelsin_transit:
                        for transit_model in modelsin_transit:
                            model_id = transit_model["model_id"]
                            quantity = transit_model["quantity"]
                            
                            cur.execute("""UPDATE cash_stock_purchase_models SET quantity_delivered = quantity_delivered + %s WHERE model_id = %s AND cash_stock_purchase_id = %s""", (quantity, model_id, stock_purchases_id))
                            mysql.get_db().commit()
                    
                    message = {'status':200,
                               'description':'Transit stock record was approved successfully!'}
                    return jsonify(message), 200  
                
            else:
                message = {'status':404,
                           'description':'Transit stock record was not found!'}
                return jsonify(message), 404
                    
        #Error handling
        except Exception as error:
            message = {'status':501,
                       'error':'sp_a09',
                       'description':'Failed to approve transit stock record. Error description ' + format(error)}
            ErrorLogger().logError(message)
            return jsonify(message), 501
        finally:
            cur.close()

     
   