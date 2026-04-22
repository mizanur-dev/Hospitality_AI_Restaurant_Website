"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  User,
  Mail,
  Shield,
  Calendar,
  X,
  LogOut,
  Pencil,
  Eye,
  EyeOff,
  Paintbrush,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import Image from "next/image";
import { ModeToggle } from "@/components/elements/ModeToggle";

const contactSchema = z.object({
  fullName: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email"),
});

const passwordSchema = z
  .object({
    newPassword: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

type ContactFormValues = z.infer<typeof contactSchema>;
type PasswordFormValues = z.infer<typeof passwordSchema>;

export default function Profile() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [profileImage, setProfileImage] = useState<string | null>(null);
  const [isEditingContact, setIsEditingContact] = useState(false);
  const [isEditingPassword, setIsEditingPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const contactForm = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      fullName: "Sarah Martinez",
      email: "sarah.martinez@restaurant.com",
    },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      newPassword: "",
      confirmPassword: "",
    },
  });

  const handleImageClick = () => fileInputRef.current?.click();

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => setProfileImage(reader.result as string);
      reader.readAsDataURL(file);
    }
  };

  const onContactSubmit = () => {
    setIsEditingContact(false);
    toast.success("Profile Updated", {
      description: "Your contact information has been saved.",
    });
  };

  const onPasswordSubmit = () => {
    setIsEditingPassword(false);
    passwordForm.reset();
    setShowNewPassword(false);
    setShowConfirmPassword(false);
    toast.success("Password Changed", {
      description: "Your password has been updated successfully.",
    });
  };

  const handleLogout = () => router.push("/");

  return (
    <div className="max-w-[1920px] mx-auto p-4 sm:p-6">
      <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            User Profile
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => window.history.back()}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        <div className="p-4 sm:p-6 space-y-8">
          {/* Profile Picture */}
          <div className="flex items-center gap-5">
            <div className="relative">
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center overflow-hidden shadow-lg">
                {profileImage ? (
                  <Image
                    fill
                    src={profileImage}
                    alt="Profile"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <User className="w-12 h-12 text-white" />
                )}
              </div>
              <button
                onClick={handleImageClick}
                className="absolute -bottom-2 -right-2 w-9 h-9 bg-purple-600 hover:bg-purple-700 rounded-full flex items-center justify-center shadow-xl transition-all"
              >
                <Pencil className="w-4 h-4 text-white" />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="hidden"
              />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                {contactForm.getValues("fullName")}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Restaurant Manager
              </p>
            </div>
          </div>

          {/* Contact Information */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Contact Information
              </h3>
            </div>

            <form
              onSubmit={contactForm.handleSubmit(onContactSubmit)}
              className="space-y-6"
            >
              <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 space-y-6">
                {/* Full Name */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <Label className="text-sm text-gray-500 dark:text-gray-400">
                      Full Name
                    </Label>
                    <Input
                      {...contactForm.register("fullName")}
                      disabled={!isEditingContact}
                      className={cn(
                        "bg-transparent border-0 text-lg font-medium text-gray-900 dark:text-white p-0 h-auto focus-visible:ring-0",
                        !isEditingContact && "cursor-default"
                      )}
                    />
                    {contactForm.formState.errors.fullName && (
                      <p className="text-sm text-red-500">
                        {contactForm.formState.errors.fullName.message}
                      </p>
                    )}
                  </div>
                  {!isEditingContact && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEditingContact(true)}
                      className="text-purple-600 hover:text-purple-700"
                    >
                      Edit
                    </Button>
                  )}
                </div>

                {/* Email */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <Label className="text-sm text-gray-500 dark:text-gray-400">
                      Email Address
                    </Label>
                    <Input
                      {...contactForm.register("email")}
                      disabled={!isEditingContact}
                      className={cn(
                        "bg-transparent border-0 text-gray-900 dark:text-white p-0 h-auto focus-visible:ring-0",
                        !isEditingContact && "cursor-default"
                      )}
                    />
                    {contactForm.formState.errors.email && (
                      <p className="text-sm text-red-500">
                        {contactForm.formState.errors.email.message}
                      </p>
                    )}
                  </div>
                </div>

                {/* Save / Cancel Buttons */}
                {isEditingContact && (
                  <div className="flex gap-3 justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        contactForm.reset();
                        setIsEditingContact(false);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      size="sm"
                      className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white"
                    >
                      Save Changes
                    </Button>
                  </div>
                )}
              </div>
            </form>
          </div>

          {/* Privacy Setting */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Privacy & Security
              </h3>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <Label className="text-sm text-gray-500 dark:text-gray-400">
                    Password
                  </Label>
                  <p className="text-gray-900 dark:text-white mt-1">
                    ************
                  </p>
                </div>
                {!isEditingPassword && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsEditingPassword(true)}
                    className="text-purple-600 hover:text-purple-700"
                  >
                    Change Password
                  </Button>
                )}
              </div>

              {isEditingPassword && (
                <form
                  onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}
                  className="space-y-5 pt-4 border-t border-gray-200 dark:border-gray-700"
                >
                  {/* New Password */}
                  <div className="space-y-2">
                    <Label>New Password</Label>
                    <div className="relative">
                      <Input
                        {...passwordForm.register("newPassword")}
                        type={showNewPassword ? "text" : "password"}
                        placeholder="Enter new password"
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showNewPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    {passwordForm.formState.errors.newPassword && (
                      <p className="text-sm text-red-500">
                        {passwordForm.formState.errors.newPassword.message}
                      </p>
                    )}
                  </div>

                  {/* Confirm Password */}
                  <div className="space-y-2">
                    <Label>Confirm New Password</Label>
                    <div className="relative">
                      <Input
                        {...passwordForm.register("confirmPassword")}
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="Confirm password"
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setShowConfirmPassword(!showConfirmPassword)
                        }
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    {passwordForm.formState.errors.confirmPassword && (
                      <p className="text-sm text-red-500">
                        {passwordForm.formState.errors.confirmPassword.message}
                      </p>
                    )}
                  </div>

                  {/* Buttons */}
                  <div className="flex gap-3 justify-end pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        passwordForm.reset();
                        setIsEditingPassword(false);
                        setShowNewPassword(false);
                        setShowConfirmPassword(false);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      size="sm"
                      className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white"
                    >
                      Save Password
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {/* Aperance */}

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Paintbrush className="w-5 h-5 text-orange-600" />
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Appearance
              </h3>
            </div>
            <ModeToggle/>
          </div>

          {/* Account Details */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-green-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Account Details
              </h3>
            </div>

            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 space-y-4">
              <div>
                <Label className="text-sm text-gray-500 dark:text-gray-400">
                  Member Since
                </Label>
                <p className="text-gray-900 dark:text-white font-medium">
                  January 2023
                </p>
              </div>
              <div>
                <Label className="text-sm text-gray-500 dark:text-gray-400">
                  Account Status
                </Label>
                <div className="flex items-center gap-2 mt-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span className="text-green-600 dark:text-green-400 font-medium">
                    Active
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Logout */}
          <div className="pt-6">
            <Button
              onClick={handleLogout}
              variant="outline"
              className="w-full border-red-500/30 bg-red-500/5 hover:bg-red-500/10 text-red-600 dark:text-red-400"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Log Out
            </Button>
            <p className="text-center text-xs text-gray-500 dark:text-gray-400 mt-3">
              You will be signed out from all devices
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
